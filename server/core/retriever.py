from core.clients import  get_qdrant
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
from core.embedding_client import embed_both, rerank_results

@observe()
async def query_codebase(question: str,repo: str, top_k: int = 5) -> list:
    text = f"File: \n\n{question}"
    results = await embed_both([text])
    dense_results = results["dense"]
    sparse_results = results["sparse"]

    results = await get_qdrant().query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            Prefetch(
                query=dense_results[0],
                using="dense",
                limit=top_k * 4,
            ),
            Prefetch(
                query=SparseVector(
                    indices=sparse_results[0][0],
                    values=sparse_results[0][1],
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

@observe()
async def rerank(question: str, results: list, top_k: int = 5) -> list:
    scores = await rerank_results(question, [r.payload["content"] for r in results])
    scored = sorted(zip(scores, results), key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:top_k]]