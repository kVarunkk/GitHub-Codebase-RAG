from dotenv import load_dotenv
load_dotenv() 
from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.clients import close_arq_pool, close_qdrant, close_redis, ensure_collection, init_deepeval, init_qdrant, init_redis, get_arq_pool
from api.routes.index import router as index_router
from api.routes.query import router as query_router
from api.routes.evaluate import router as evaluate_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await get_arq_pool()
    await init_redis()
    await init_qdrant()
    await ensure_collection()
    init_deepeval()
    yield
    # shutdown
    await close_redis()
    await close_arq_pool()
    await close_qdrant()

app = FastAPI(
    title="GitHub RAG APP",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(index_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(evaluate_router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}