import httpx
import os

EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8001")

async def embed_both(texts: list[str]) -> dict:
    async with httpx.AsyncClient(timeout=100) as client:
        response = await client.post(f"{EMBEDDING_SERVICE_URL}/embed/both", json={"texts": texts})
        response.raise_for_status()
        return response.json()

async def rerank_results(question: str, chunks: list[str]) -> list[float]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{EMBEDDING_SERVICE_URL}/rerank",
            json={"question": question, "chunks": chunks}
        )
        response.raise_for_status()
        return response.json()["scores"]