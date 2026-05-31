import uuid
from qdrant_client.models import PointStruct, SparseVector
from core.clients import qdrant
from constants import COLLECTION_NAME

async def store_chunks(chunks: list, repo: str):
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
            }
        )
        for chunk in chunks
    ]

    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        await qdrant.upsert(collection_name=COLLECTION_NAME, points=batch)
        print(f"  uploaded {min(i + batch_size, len(points))}/{len(points)}")

    print("[indexer] Done.")