import uuid
from qdrant_client.models import PointStruct, SparseVector
from core.clients import get_qdrant
from constants import COLLECTION_NAME

async def store_chunks(chunks: list, repo: str, progress_callback=None):
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector={
                "dense": chunk["embedding"],
                "sparse": SparseVector(
                    indices=chunk["sparse_indices"],
                    values=chunk["sparse_values"],
                )
            },
            payload={
                "repo": repo,
                "path": chunk["path"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "content": chunk["content"],
                "file_hash": chunk["file_hash"]
            }
        )
        for chunk in chunks
    ]

    batch_size = 100
    stored = 0
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        await get_qdrant().upsert(collection_name=COLLECTION_NAME, points=batch)
        stored+=len(batch)
        if progress_callback:
            progress_callback(stored_chunks=stored)

    print("[indexer] Chunks stored. Indexing complete!")