import hashlib
from qdrant_client.models import Filter, FieldCondition, FilterSelector, MatchAny, MatchValue
from core.clients import get_qdrant
from constants import COLLECTION_NAME

def get_file_hash(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()

async def get_existing_file_hashes(repo: str) -> dict[str, str]:
    """Returns {path: file_hash} for all indexed files in this repo"""
    existing = {}
    offset = None

    while True:
        results, next_offset = await get_qdrant().scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="repo", match=MatchValue(value=repo))]
            ),
            limit=100,
            offset=offset,
            with_payload=["path", "file_hash"],
            with_vectors=False,
        )

        for point in results:
            if point.payload is None:
                continue
            path = point.payload["path"]
            file_hash = point.payload.get("file_hash")
            if file_hash:
                existing[path] = file_hash

        if next_offset is None:
            break
        offset = next_offset

    return existing


async def delete_vectors_for_paths(repo: str, paths: list[str]):
    if not paths:
        return
    await get_qdrant().delete(
        collection_name=COLLECTION_NAME,
        points_selector=FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(key="repo", match=MatchValue(value=repo)),
                    FieldCondition(key="path", match=MatchAny(any=paths)),
                ]
            )
        )
    )
    print(f"[indexer] Deleted vectors for {len(paths)} files")


async def diff_files(files: list, repo: str) -> tuple[list, list]:
    """
    Returns (files_to_index, paths_to_delete)
    files_to_index — new or changed files
    paths_to_delete — files that no longer exist in repo
    """
    existing_hashes = await get_existing_file_hashes(repo)
    current_paths = {f["path"] for f in files}

    files_to_index = []
    for file in files:
        existing_hash = existing_hashes.get(file["path"])
        new_hash = get_file_hash(file["content"])

        if existing_hash != new_hash:
            files_to_index.append(file)

    paths_to_delete = [
        path for path in existing_hashes
        if path not in current_paths
    ]

    return files_to_index, paths_to_delete