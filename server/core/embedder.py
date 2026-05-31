from concurrent.futures import ThreadPoolExecutor
from core.clients import dense_model, sparse_model

def embed_chunks(chunks: list, batch_size: int = 32) -> list:
    """
    Runs dense and sparse embedding in parallel.
    """
    def run_dense(chunks):
        texts = [f"File: {chunk['path']}\n\n{chunk['content']}" for chunk in chunks]
        print(f"[Dense] Embedding {len(texts)} chunks...")
        embeddings = dense_model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        for i, chunk in enumerate(chunks):
            chunk["embedding"] = embeddings[i].tolist()
        print(f"[Dense] Done. Dim: {len(chunks[0]['embedding'])}")

    def run_sparse(chunks):
        texts = [f"File: {chunk['path']}\n\n{chunk['content']}" for chunk in chunks]
        print(f"[Sparse] Embedding {len(texts)} chunks...")
        sparse_embeddings = list(sparse_model.embed(texts))
        for i, chunk in enumerate(chunks):
            chunk["sparse_indices"] = sparse_embeddings[i].indices.tolist()
            chunk["sparse_values"] = sparse_embeddings[i].values.tolist()
        print("[Sparse] Done.")

    with ThreadPoolExecutor(max_workers=2) as executor:
        dense_future = executor.submit(run_dense, chunks)
        sparse_future = executor.submit(run_sparse, chunks)

        dense_future.result()
        sparse_future.result()

    return chunks
