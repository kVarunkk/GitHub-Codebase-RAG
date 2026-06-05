import base64
import asyncio
import httpx
from constants import CODE_EXTENSIONS
from core.chunker import chunk_all_files
from core.embedder import  process_indexing_batch
from core.store_chunk import store_chunks
import os
from core.idempotency_checker import delete_vectors_for_paths, diff_files

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


async def fetch_file_content(client: httpx.AsyncClient, file_url: str, semaphore: asyncio.Semaphore) -> str | None:
    async with semaphore:
        for attempt in range(3):  
            try:
                response = await client.get(file_url, headers=GITHUB_HEADERS)
                
                if response.status_code == 403 or response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    await asyncio.sleep(retry_after)
                    continue
                    
                if response.status_code != 200:
                    return None
                    
                data = response.json()
                content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
                return content
                
            except httpx.HTTPError:
                await asyncio.sleep(1 * (attempt + 1))  
        return None

async def fetch_all_code_files(owner: str, repo: str, branch: str = "main", progress_callback=None) -> list:
    # Limits maximum parallel requests to 20. Safe for GitHub secondary limits.
    MAX_CONCURRENT_REQUESTS = 20
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async with httpx.AsyncClient(timeout=30) as client:
        tree = await get_repo_tree(client, owner, repo, branch)
        code_files = filter_code_files(tree)
        total_files = len(code_files)
        print(f"Found {total_files} code files")

        if progress_callback:
            progress_callback(total_files=total_files, fetched_files=0)

        tasks = []
        fetched_count = 0 

        for file in code_files:
            async def worker(f=file):
                nonlocal fetched_count
                content = await fetch_file_content(client, f["url"], semaphore)
                fetched_count += 1
                if progress_callback:
                    progress_callback(fetched_files=fetched_count) 
                return {"path": f["path"], "content": content} if content else None
            
            tasks.append(worker())

        raw_results = await asyncio.gather(*tasks)
        
        results = [r for r in raw_results if r is not None]

        print(f"Fetched {len(results)} files")
        return results
    

async def run_indexing_pipeline(owner: str, repo: str, branch: str = "main", progress_callback=None):
    repo_full = f"{owner}/{repo}"
    print(f"[indexer] Starting: {repo_full} ({branch})")

    files = await fetch_all_code_files(owner, repo, branch, progress_callback=progress_callback)
    print(f"[indexer] Fetched {len(files)} files")

    # diff against existing index
    files_to_index, paths_to_delete = await diff_files(files, repo_full)
    print(f"[indexer] {len(files_to_index)} changed/new, {len(paths_to_delete)} deleted, {len(files) - len(files_to_index)} unchanged — skipping")

    # delete vectors for changed + deleted files
    changed_paths = [f["path"] for f in files_to_index]
    await delete_vectors_for_paths(repo_full, changed_paths + paths_to_delete)

    if not files_to_index:
        print("[indexer] Nothing to update.")
        return

    # CPU bound
    loop = asyncio.get_event_loop()
    chunks = await loop.run_in_executor(None, chunk_all_files, files_to_index)
    print(f"[indexer] Created {len(chunks)} chunks")

    if progress_callback:
        progress_callback(chunked_files=len(files_to_index))

    # CPU bound
    chunks = await process_indexing_batch(chunks)
    print(f"[indexer] Embedded {len(chunks)} chunks")

    if progress_callback:
        progress_callback(embedded_chunks=len(chunks))

    await store_chunks(chunks, repo_full, progress_callback=progress_callback)

     