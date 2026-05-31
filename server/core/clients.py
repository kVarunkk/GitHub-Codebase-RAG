from dotenv import load_dotenv
load_dotenv()
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import (
    Distance, VectorParams,
    SparseVectorParams, SparseIndexParams
)
from fastembed import SparseTextEmbedding
from sentence_transformers import SentenceTransformer,CrossEncoder
import os
from constants import COLLECTION_NAME, VECTOR_DIM
from google import genai


# --- Qdrant ---
qdrant = AsyncQdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

# --- Embedding models ---
dense_model = SentenceTransformer("all-MiniLM-L6-v2")
sparse_model = SparseTextEmbedding("Qdrant/bm42-all-minilm-l6-v2-attentions")
rerank_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# --- Gemini ---
gemini = genai.Client(api_key=os.getenv('GOOGLE_API_KEY') )

# --- Collection setup ---
async def ensure_collection():
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
    print(f"[Qdrant] Payload index on 'repo' created.")  