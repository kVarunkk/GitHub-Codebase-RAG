import os
from dotenv import load_dotenv
load_dotenv()
import asyncio
from core.clients import close_qdrant, close_redis, ensure_collection, init_qdrant, init_redis
from arq.connections import RedisSettings
from core.indexer import run_indexing_pipeline
from core.database import update_job_status, update_job_progress
from api.models import IndexStatus

async def startup(ctx):
    await init_redis()
    await init_qdrant()
    await ensure_collection()
    print("[Worker] Startup complete.")

async def shutdown(ctx):
    await close_redis()
    await close_qdrant()
    print("[Worker] Shutdown complete.")

async def index_repo_task(ctx, job_id: str, owner: str, repo: str, branch: str):
    """ARQ task — runs in worker process"""
    try:
        await update_job_status(job_id, IndexStatus.RUNNING)

        def progress_callback(**kwargs):
            asyncio.create_task(update_job_progress(job_id, kwargs))

        await run_indexing_pipeline(owner, repo, branch, progress_callback=progress_callback)
        await update_job_status(job_id, IndexStatus.DONE, message=f"Successfully indexed {owner}/{repo}")

    except Exception as e:
        await update_job_status(job_id, IndexStatus.FAILED, message=str(e))
        raise


class WorkerSettings:
    functions = [index_repo_task]
    on_startup = startup
    on_shutdown = shutdown 
    redis_settings = RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379"))
    max_jobs = 4          # max concurrent jobs per worker process
    job_timeout = 3600    # 1 hour max per job
    retry_jobs = False    # don't auto retry failed jobs