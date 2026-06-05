import json
from api.models import IndexStatus
from core.clients import get_redis

JOB_TTL = 60 * 60 * 24 

async def create_job(job_id: str, owner: str, repo: str) -> None:
    r = get_redis()
    job = {
        "job_id": job_id,
        "repo": f"{owner}/{repo}",
        "status": IndexStatus.PENDING,
        "message": "",
        "progress": json.dumps({
            "total_files": 0,
            "fetched_files": 0,
            "chunked_files": 0,
            "embedded_chunks": 0,
            "stored_chunks": 0,
        })
    }
    await r.hset(f"job:{job_id}", mapping=job)  # type: ignore
    await r.expire(f"job:{job_id}", JOB_TTL)


async def update_job_status(job_id: str, status: IndexStatus, message: str = "") -> None:
    r = get_redis()
    await r.hset(f"job:{job_id}", mapping={
        "status": status,
        "message": message or "",
    })  # type: ignore


async def update_job_progress(job_id: str, progress: dict) -> None:
    r = get_redis()
    # fetch current, merge, store back
    current_raw = await r.hget(f"job:{job_id}", "progress")  # type: ignore
    current = json.loads(current_raw) if current_raw else {}
    current.update(progress)
    await r.hset(f"job:{job_id}", "progress", json.dumps(current))  # type: ignore


async def get_job(job_id: str) -> dict | None:
    r = get_redis()
    job = await r.hgetall(f"job:{job_id}")  # type: ignore
    if not job:
        return None
    return {
        "job_id": job["job_id"],
        "repo": job["repo"],
        "status": job["status"],
        "message": job["message"],
        "progress": json.loads(job["progress"]),
    }