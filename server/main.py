from dotenv import load_dotenv
load_dotenv() 
from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.clients import ensure_collection
from api.routes.index import router as index_router
from api.routes.query import router as query_router
import deepeval
import os

confident_api_key = os.getenv("CONFIDENT_API_KEY")
if confident_api_key:
    deepeval.login(api_key=confident_api_key)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_collection()
    yield

app = FastAPI(
    title="GitHub RAG APP",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(index_router, prefix="/api")
app.include_router(query_router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}