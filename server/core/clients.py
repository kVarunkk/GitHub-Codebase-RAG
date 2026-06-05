from dotenv import load_dotenv
load_dotenv()
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import (
    Distance, VectorParams,
    SparseVectorParams, SparseIndexParams
)
import os
from constants import COLLECTION_NAME, VECTOR_DIM
from google import genai
import deepeval
from arq.connections import create_pool, RedisSettings
import redis.asyncio as aioredis

_arq_pool = None 
_redis: aioredis.Redis | None = None
_qdrant: AsyncQdrantClient | None = None

# --- Redis client setup ---
def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis
async def init_redis():
    global _redis
    _redis = aioredis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"),
        encoding="utf-8",
        decode_responses=True
    )
    await _redis.ping() 
    print("[Redis] Connected.")
async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        print("[Redis] Connection closed.")

# --- ARQ setup ---
async def get_arq_pool():
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(
            RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379"))
        )
    return _arq_pool
async def close_arq_pool():
    global _arq_pool
    if _arq_pool:
        await _arq_pool.aclose()
        _arq_pool = None
        print("[ARQ] Pool closed.")

# --- Qdrant client setup ---
def get_qdrant():
    if _qdrant is None:
        raise RuntimeError("Qdrant not initialized")
    return _qdrant
async def init_qdrant():
    global _qdrant

    _qdrant = AsyncQdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
async def close_qdrant():
    global _qdrant

    if _qdrant:
        await _qdrant.close()
        _qdrant = None 

# --- Deepeval setup for tracing---
def init_deepeval():
   confident_api_key = os.getenv("CONFIDENT_API_KEY")
   if confident_api_key:
      deepeval.login(api_key=confident_api_key) 

# --- Gemini ---
gemini = genai.Client(api_key=os.getenv('GOOGLE_API_KEY') )

# --- Collection setup ---
async def ensure_collection():
    qdrant = get_qdrant()
    existing = [c.name for c in (await qdrant.get_collections()).collections]
    if COLLECTION_NAME not in existing:
        await qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "dense": VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))
            },
            hnsw_config=models.HnswConfigDiff(
              payload_m=16,
              m=0,
            ),
        )
        
        print(f"[Qdrant] Collection '{COLLECTION_NAME}' created.")
    else:
        print(f"[Qdrant] Collection '{COLLECTION_NAME}' already exists.")

    await qdrant.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="repo",
        field_schema=models.KeywordIndexParams(
            type=models.KeywordIndexType.KEYWORD,
            is_tenant=True,
        ),
    )

    await qdrant.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="path",
        field_schema=models.KeywordIndexParams(
            type=models.KeywordIndexType.KEYWORD,
        ),
    )
    print(f"[Qdrant] Payload index on 'repo' and 'path' created.")  