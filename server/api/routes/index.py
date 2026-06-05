from fastapi import APIRouter, HTTPException
from api.models import IndexProgress, IndexRequest, IndexStatus, IndexStatusResponse
import uuid
from core.clients import get_arq_pool, get_qdrant
from qdrant_client.models import Filter, FieldCondition, MatchValue, FilterSelector
from constants import COLLECTION_NAME
from core.database import create_job, get_job

router = APIRouter()

def parse_repo_url(repo_url: str) -> tuple[str, str]:
    # "https://github.com/kVarunkk/GetHired" → ("kVarunkk", "GetHired")
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")
    return parts[-2], parts[-1]


@router.post("/index", response_model=IndexStatusResponse)
async def index_repo(body: IndexRequest):
    try:
        owner, repo = parse_repo_url(body.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id = str(uuid.uuid4())

    # save job to DB
    await create_job(job_id, owner, repo)

    # enqueue task in Redis — ARQ worker picks it up
    pool = await get_arq_pool()
    await pool.enqueue_job(
        "index_repo_task",
        job_id,
        owner,
        repo,
        body.branch,
        _job_id=job_id  # use same id in ARQ so it's traceable
    )

    return IndexStatusResponse(
        job_id=job_id,
        status=IndexStatus.PENDING,
        message=f"Indexing queued for {owner}/{repo}"
    )


@router.get("/index/{job_id}", response_model=IndexStatusResponse)
async def get_index_status(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return IndexStatusResponse(
        job_id=job_id,
        status=job["status"],
        message=job.get("message"),
        progress=IndexProgress(**job["progress"]) if job.get("progress") else None
    )


# api/routes/index.py
@router.delete("/index")
async def delete_repo_index(repo: str):
    # repo = "kVarunkk/GetHired-mcp-server"
    try:
        await get_qdrant().delete(
            collection_name=COLLECTION_NAME,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="repo", match=MatchValue(value=repo))]
                )
            )
        )
        return {"success": True, "message": f"Deleted all points for {repo}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    