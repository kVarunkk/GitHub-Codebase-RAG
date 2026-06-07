import time
from core.embedding_client import embed_both

async def process_indexing_batch(chunks, batch_size=100):
    start = time.perf_counter()
    all_dense = []
    all_sparse = []

    total_batches = (len(chunks) + batch_size - 1) // batch_size
    print(f"[Embedder] Starting {total_batches} batches for {len(chunks)} chunks")

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [f"File: {chunk['path']}\n\n{chunk['content']}" for chunk in batch]
        
        print(f"[Embedder] Batch {i // batch_size + 1}/{(len(chunks) + batch_size - 1) // batch_size}")
        result = await embed_both(texts)

        print(f"result length: {len(result['dense'])}, {len(result['sparse'])}")
        
        all_dense.extend(result["dense"])
        all_sparse.extend(result["sparse"])

    for i, chunk in enumerate(chunks):
        chunk["embedding"] = all_dense[i]
        chunk["sparse_indices"] = all_sparse[i][0]
        chunk["sparse_values"] = all_sparse[i][1]

    elapsed = time.perf_counter() - start
    print(f"\n[indexer] Embedded {len(chunks)} chunks TOTAL TIME: {elapsed:.2f}s\n")
    return chunks
