import asyncio
from functools import partial
from core.clients import  dense_model, sparse_model, qdrant, rerank_model
from constants import COLLECTION_NAME
from qdrant_client.models import (
    SparseVector,
    FusionQuery,
    Prefetch,
    Fusion,
    Filter,
    FieldCondition,
    MatchValue,
)
from deepeval.tracing import observe

@observe()
async def query_codebase(question: str,repo: str, top_k: int = 5) -> list:
    text = f"File: \n\n{question}"
    loop = asyncio.get_event_loop()

    dense_embedding, sparse_embedding = await asyncio.gather(
        loop.run_in_executor(None, lambda: dense_model.encode(text, convert_to_numpy=True).tolist()),
        loop.run_in_executor(None, lambda: list(sparse_model.embed([text]))[0])
    )

    results = await qdrant.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            Prefetch(
                query=dense_embedding,
                using="dense",
                limit=top_k * 4,
            ),
            Prefetch(
                query=SparseVector(
                    indices=sparse_embedding.indices.tolist(),
                    values=sparse_embedding.values.tolist(),
                ),
                using="sparse",
                limit=top_k * 4,
            ),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        query_filter=Filter(
            must=[FieldCondition(key="repo", match=MatchValue(value=repo))]
        ),
        limit=top_k,
        with_payload=True,
    )
    return results.points

@observe()
def build_context(results: list) -> str:
    context = ""
    for r in results:
        context += f"### File: {r.payload['path']} (lines {r.payload['start_line']}–{r.payload['end_line']})\n"
        context += r.payload['content']
        context += "\n\n"
    return context

def rerank(question: str, results: list, top_k: int = 5) -> list:
    pairs = [(question, r.payload["content"]) for r in results]
    scores = rerank_model.predict(pairs)
    scored = sorted(zip(scores, results), key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:top_k]]

@observe()
async def rerank_async(question: str, results: list, top_k: int = 5) -> list:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        partial(rerank, question, results, top_k)
    )