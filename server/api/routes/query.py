from fastapi import APIRouter, HTTPException
from api.models import QueryRequest, QueryResponse
from core.generator import ask

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query(body: QueryRequest):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    if not body.repo.strip():
        raise HTTPException(status_code=400, detail="Repo cannot be empty")

    try:
        answer, chunks = await ask(
            question=body.question,
            repo=body.repo,
            candidate_k=body.candidate_k,
            final_k=body.final_k,
        )

        citations = [
            {
                "path": r.payload["path"],
                "start_line": r.payload["start_line"],
                "end_line": r.payload["end_line"],
            }
            for r in chunks  
        ]

        return QueryResponse(answer=answer, citations=citations)

    except Exception as e:
        print(f"[query] Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))