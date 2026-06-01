import base64
import asyncio
import httpx
from constants import CODE_EXTENSIONS
from core.chunker import chunk_all_files
from core.embedder import embed_chunks
from core.store_chunk import store_chunks
import os

GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
}

async def get_repo_tree(client: httpx.AsyncClient, owner: str, repo: str, branch: str = "main") -> dict:
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    response = await client.get(url, headers=GITHUB_HEADERS)
    response.raise_for_status()
    return response.json()


def filter_code_files(tree: dict) -> list:
    files = []
    for item in tree["tree"]:
        if item["type"] != "blob":
            continue
        path = item["path"]
        ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
        if ext in CODE_EXTENSIONS:
            files.append(item)
    return files


async def fetch_file_content(client: httpx.AsyncClient, file_url: str) -> str | None:
    response = await client.get(file_url, headers=GITHUB_HEADERS)
    if response.status_code != 200:
        return None
    data = response.json()
    # binary -> base64 -> utf-8 string
    return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")


async def fetch_all_code_files(owner: str, repo: str, branch: str = "main", progress_callback=None) -> list:
    async with httpx.AsyncClient(timeout=30) as client:
        tree = await get_repo_tree(client, owner, repo, branch)
        code_files = filter_code_files(tree)
        print(f"Found {len(code_files)} code files")

        if progress_callback:
            progress_callback(total_files=len(code_files), fetched_files=0)

        results = []
        for file in code_files:
            content = await fetch_file_content(client, file["url"])
            if content:
                results.append({
                    "path": file["path"],
                    "content": content,
                })
            if progress_callback:
                progress_callback(fetched_files=len(results))
                
            await asyncio.sleep(1)

        print(f"Fetched {len(results)} files")
        return results
    

async def run_indexing_pipeline(owner: str, repo: str, branch: str = "main", progress_callback=None):
    repo_full = f"{owner}/{repo}"
    print(f"[indexer] Starting: {repo_full} ({branch})")

    # I/O bound
    files = await fetch_all_code_files(owner, repo, branch, progress_callback=progress_callback)
    print(f"[indexer] Fetched {len(files)} files")

    # CPU bound — run in threadpool 
    loop = asyncio.get_event_loop()
    chunks = await loop.run_in_executor(None, chunk_all_files, files)
    print(f"[indexer] Created {len(chunks)} chunks")

    # update chunked files
    if progress_callback:
        progress_callback(chunked_files=len(files))

    # CPU bound
    chunks = await loop.run_in_executor(None, embed_chunks, chunks)
    print(f"[indexer] Embedded {len(chunks)} chunks")

    # update embedded chunks
    if progress_callback:
        progress_callback(embedded_chunks=len(chunks))

    # I/O bound
    await store_chunks(chunks, repo_full, progress_callback=progress_callback)

     