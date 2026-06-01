from fastapi import APIRouter, BackgroundTasks, HTTPException
from api.models import IndexProgress, IndexRequest, IndexStatus, IndexStatusResponse
from core.indexer import run_indexing_pipeline
import uuid
from core.clients import qdrant
from qdrant_client.models import Filter, FieldCondition, MatchValue, FilterSelector
from constants import COLLECTION_NAME

router = APIRouter()

# in memory job store
jobs: dict[str, dict] = {}

def parse_repo_url(repo_url: str) -> tuple[str, str]:
    # "https://github.com/kVarunkk/GetHired" → ("kVarunkk", "GetHired")
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")
    return parts[-2], parts[-1]

async def indexing_task(job_id: str, owner: str, repo: str, branch: str):
    jobs[job_id]["status"] = IndexStatus.RUNNING

    def update_progress(**kwargs):
        for key, value in kwargs.items():
            jobs[job_id]["progress"][key] = value

    try:
        await run_indexing_pipeline(owner, repo, branch, progress_callback=update_progress)
        jobs[job_id]["status"] = IndexStatus.DONE
        jobs[job_id]["message"] = f"Successfully indexed {owner}/{repo}"
    except Exception as e:
        jobs[job_id]["status"] = IndexStatus.FAILED
        jobs[job_id]["message"] = str(e)
        print(f"[indexer] Failed for {owner}/{repo}: {e}")

@router.post("/index", response_model=IndexStatusResponse)
async def index_repo(body: IndexRequest, background_tasks: BackgroundTasks):
    try:
        owner, repo = parse_repo_url(body.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": IndexStatus.PENDING,
        "message": f"Queued indexing for {owner}/{repo}",
        "progress": {
            "total_files": 0,
            "fetched_files": 0,
            "chunked_files": 0,
            "embedded_chunks": 0,
            "stored_chunks": 0,
        }
    }

    background_tasks.add_task(indexing_task, job_id, owner, repo, body.branch)

    return IndexStatusResponse(
        job_id=job_id,
        status=IndexStatus.PENDING,
        message=f"Indexing started for {owner}/{repo}"
    )

@router.get("/index/{job_id}", response_model=IndexStatusResponse)
async def get_index_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return IndexStatusResponse(
        job_id=job_id,
        status=job["status"],
        message=job["message"],
        progress=IndexProgress(**job["progress"])
    )


# api/routes/index.py
@router.delete("/index")
async def delete_repo_index(repo: str):
    # repo = "kVarunkk/GetHired-mcp-server"
    try:
        await qdrant.delete(
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