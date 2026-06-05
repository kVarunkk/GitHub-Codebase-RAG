from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, CrossEncoder
from fastembed import SparseTextEmbedding
import asyncio

app = FastAPI(
    title="Embedding Service",
    version="1.0.0",
)

dense_model = SentenceTransformer("all-MiniLM-L6-v2")
sparse_model = SparseTextEmbedding("Qdrant/bm42-all-minilm-l6-v2-attentions")
rerank_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

class EmbedRequest(BaseModel):
    texts: list[str]

class RerankRequest(BaseModel):
    question: str
    chunks: list[str]

@app.post("/embed/dense")
async def embed_dense(body: EmbedRequest):
    embeddings = await asyncio.to_thread(
        dense_model.encode, body.texts, convert_to_numpy=True
    )
    return {"embeddings": [e.tolist() for e in embeddings]}

@app.post("/embed/sparse")
async def embed_sparse(body: EmbedRequest):
    results = await asyncio.to_thread(list, sparse_model.embed(body.texts))
    return {
        "embeddings": [
            {"indices": r.indices.tolist(), "values": r.values.tolist()}
            for r in results
        ]
    }

@app.post("/embed/both")
async def embed_both(body: EmbedRequest):
    dense, sparse = await asyncio.gather(
        asyncio.to_thread(dense_model.encode, body.texts, convert_to_numpy=True, show_progress_bar=True),
        asyncio.to_thread(list, sparse_model.embed(body.texts))
    )
    return {
        "dense": [e.tolist() for e in dense],
        "sparse": [
            (r.indices.tolist(), r.values.tolist())
            for r in sparse
        ]
    }

@app.post("/rerank")
async def rerank(body: RerankRequest):
    pairs = [(body.question, chunk) for chunk in body.chunks]
    scores = await asyncio.to_thread(rerank_model.predict, pairs)
    return {"scores": scores.tolist()}

@app.get("/health")
async def health():
    return {"status": "ok"}