# GitHub RAG App

A production-grade **Retrieval-Augmented Generation (RAG)** system that lets you ask questions about any GitHub repository and get accurate answers with file and line number citations.

> **Repo:** [github.com/kVarunkk/GitHub-Codebase-RAG](https://github.com/kVarunkk/GitHub-Codebase-RAG)

---

## How It Works

1. Paste a GitHub repo URL — the app fetches all code files via the GitHub API
2. Files are parsed using **tree-sitter** (AST-aware chunking by function/class boundaries)
3. Each chunk is embedded using both **dense** (semantic) and **sparse** (BM42 keyword) vectors
4. Vectors are stored in **Qdrant Cloud** with repo-level tenant isolation
5. When you ask a question, hybrid search (RRF fusion) retrieves the most relevant chunks
6. A **cross-encoder re-ranker** re-scores results for precision
7. **Gemini** generates an answer grounded strictly in retrieved chunks, with file + line citations

---

## Architecture

```
Client (curl / API)
        │
        ▼
┌───────────────────┐
│   FastAPI Server  │  handles HTTP, query, evaluate
│   (api service)   │
└────────┬──────────┘
         │ enqueue job
         ▼
┌───────────────────┐
│      Redis        │  job queue + job state storage
└────────┬──────────┘
         │ poll + dequeue
         ▼
┌───────────────────┐
│   ARQ Worker      │  runs indexing pipeline
│ (worker service)  │
└────────┬──────────┘
         │ HTTP (embed/rerank)
         ▼
┌───────────────────┐
│ Embedding Service │  dense + sparse embeddings, reranking
│ (embedding svc)   │  models loaded once, shared by all
└───────────────────┘
         │
         ▼
┌───────────────────┐
│   Qdrant Cloud    │  vector storage, hybrid search
└───────────────────┘
```

---

## Features

**AST-aware chunking**
Uses tree-sitter to split code at function and class boundaries. Supports TypeScript, TSX, JavaScript, Python, Go, Rust, Java, C, and C++. Falls back to line-based chunking for unsupported types.

**Hybrid search**
Combines dense vector search (semantic similarity) with BM42 sparse keyword search, fused via Reciprocal Rank Fusion (RRF). Catches both meaning-level queries and exact matches like function names.

**Cross-encoder re-ranking**
After retrieval, a `cross-encoder/ms-marco-MiniLM-L-6-v2` model re-scores candidates by reading the question and chunk together — significantly improving result precision over vector similarity alone.

**Multi-repo support**
All repos share one Qdrant collection, isolated by a `repo` payload field with a keyword tenant index. Each query is scoped to the repo you specify.

**Idempotent re-indexing**
File hashes are stored in Redis per repo. On re-index, only changed or new files are re-embedded. Deleted files are removed from Qdrant. Unchanged files are skipped entirely.

**Microservices architecture**
Three independent services — API server, ARQ worker, and embedding service. Embedding models are loaded once in the embedding service and shared by both the API (for query-time embedding) and the worker (for indexing). No model duplication across processes.

**Async pipeline**
Built on FastAPI with full async support. CPU-bound work (embedding, reranking) runs in threadpool executors via `asyncio.to_thread`. Network I/O (GitHub API, Qdrant, Gemini, Redis) is fully async.

**Job queue with retries**
`POST /api/index` returns immediately. Indexing runs as an ARQ background job. Failed jobs retry up to 3 times with exponential backoff. Job state (status, progress) stored in Redis with 24hr TTL.

**Indexing progress tracking**
Poll `GET /api/index/{job_id}` to get real-time progress — total files, fetched, chunked, embedded, and stored counts.

**RAG evaluation endpoint**
Dedicated `/api/evaluate` scores pipeline quality using DeepEval — faithfulness, answer relevancy, contextual precision, and contextual recall. Separate from the query hot path.

**Tracing**
Every query request is traced end-to-end using DeepEval's `@observe` decorator — agent → retriever → reranker → LLM — visible in the Confident AI dashboard.

---

## Tech Stack

| Layer                | Technology                                            |
| -------------------- | ----------------------------------------------------- |
| API Server           | FastAPI (Python)                                      |
| Job Queue            | ARQ + Redis                                           |
| Vector DB            | Qdrant Cloud                                          |
| Dense Embeddings     | `all-MiniLM-L6-v2` (sentence-transformers)            |
| Sparse Embeddings    | `Qdrant/bm42-all-minilm-l6-v2-attentions` (fastembed) |
| Re-ranking           | `cross-encoder/ms-marco-MiniLM-L-6-v2`                |
| AST Parsing          | tree-sitter + tree-sitter-language-pack               |
| LLM                  | Gemini 2.5 Flash (Google AI Studio)                   |
| Tracing + Evaluation | DeepEval + Confident AI                               |
| Async HTTP           | httpx                                                 |
| Containerization     | Docker + Docker Compose                               |

---

## Project Structure

```
gh-rag-app/
├── docker-compose.yml
├── README.md
│
├── server/
│   ├── main.py                  # FastAPI app, lifespan, routes
│   ├── constants.py             # Extensions, node types, blocked dirs
│   ├── worker.py                # ARQ worker settings + task
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env
│   ├── core/
│   │   ├── clients.py           # Qdrant, Gemini, Redis, ARQ pool
│   │   ├── database.py          # Redis job state operations
│   │   ├── fetcher.py           # GitHub API — fetch repo file tree
│   │   ├── chunker.py           # tree-sitter AST chunking
│   │   ├── embedder.py          # Calls embedding service, batched
│   │   ├── embedding_client.py  # HTTP client for embedding service
│   │   ├── retriever.py         # Hybrid search, reranking, ask()
│   │   ├── generator.py         # Prompt building + Gemini call
│   │   └── indexer.py           # Full indexing pipeline
│   └── api/
│       ├── models.py            # Pydantic request/response models
│       └── routes/
│           ├── index.py         # POST /api/index, GET, DELETE
│           ├── query.py         # POST /api/query
│           └── evaluate.py      # POST /api/evaluate
│
└── embedding_service/
    ├── main.py                  # FastAPI embedding + rerank endpoints
    ├── requirements.txt
    └── Dockerfile
```

---

## Setup

### Prerequisites

- Python 3.11
- Docker Desktop (for Docker setup)
- [Qdrant Cloud](https://cloud.qdrant.io) free cluster
- [Google AI Studio](https://aistudio.google.com) API key
- [Upstash Redis](https://upstash.com) free instance (or local Redis)
- [Confident AI](https://app.confident-ai.com) account (optional, for tracing)
- GitHub Personal Access Token (optional, for higher rate limits)

---

### Option 1 — Local (without Docker)

**1. Clone the repo**

```bash
git clone https://github.com/kVarunkk/GitHub-Codebase-RAG.git
cd GitHub-Codebase-RAG
```

**2. Set up server**

```bash
cd server
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

**3. Set up embedding service**

```bash
cd ../embedding_service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**4. Configure environment variables**

Create `server/.env`:

```env
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
GOOGLE_API_KEY=your-ai-studio-api-key
GITHUB_TOKEN=your-github-pat
REDIS_URL=redis://localhost:6379
EMBEDDING_SERVICE_URL=http://localhost:8001
CONFIDENT_API_KEY=your-confident-ai-key
```

**5. Run all three services in separate terminals**

```bash
# Terminal 1 — embedding service
cd embedding_service && uvicorn main:app --port 8001 --reload

# Terminal 2 — API server
cd server && uvicorn main:app --port 8000 --reload

# Terminal 3 — ARQ worker
cd server && python -u -m arq worker.WorkerSettings
```

---

### Option 2 — Docker Compose

**1. Clone the repo**

```bash
git clone https://github.com/kVarunkk/GitHub-Codebase-RAG.git
cd GitHub-Codebase-RAG
```

**2. Configure environment variables**

Create `server/.env` with the same variables as above, but update:

```env
REDIS_URL=redis://redis:6379
EMBEDDING_SERVICE_URL=http://embedding:8001
```

**3. Build and run**

```bash
docker compose up --build
```

**4. Subsequent runs (no code changes)**

```bash
docker compose up
```

**5. Stop**

```bash
docker compose down
```

**View logs:**

```bash
docker compose logs -f          # all services
docker compose logs -f worker   # worker only
docker compose logs -f api      # api only
```

---

## API Reference

### `GET /health`

```json
{ "status": "ok" }
```

---

### `POST /api/index`

Start indexing a GitHub repository. Returns immediately — indexing runs in background.

**Request:**

```json
{
  "repo_url": "https://github.com/owner/repo",
  "branch": "main"
}
```

**Response:**

```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Indexing queued for owner/repo"
}
```

---

### `GET /api/index/{job_id}`

Poll indexing status and progress.

**Response:**

```json
{
  "job_id": "uuid",
  "status": "running",
  "message": "Attempt 1",
  "progress": {
    "total_files": 333,
    "fetched_files": 210,
    "chunked_files": 210,
    "embedded_chunks": 800,
    "stored_chunks": 700
  }
}
```

Status values: `pending` | `running` | `done` | `failed`

---

### `GET /api/index/repos`

Returns a list of all unique repository identifiers that have been successfully chunked and stored inside the vector database.

**Response:**

```json
{
  "success": "true",
  "repos": ["repo1", "repo2", ...],
  "count": 5
}
```

---

### `DELETE /api/index?repo={owner/repo}`

Delete all indexed vectors for a specific repo.

**Example:**

```bash
curl -X DELETE "http://localhost:8000/api/index?repo=owner/repo"
```

**Response:**

```json
{
  "success": true,
  "message": "Deleted all points for owner/repo"
}
```

---

### `POST /api/query`

Ask a question about an indexed repository.

**Request:**

```json
{
  "question": "How does authentication work?",
  "repo": "owner/repo",
  "candidate_k": 20,
  "final_k": 5
}
```

**Response:**

```json
{
  "answer": "Authentication uses bearer tokens validated by requireBearerAuth middleware...",
  "citations": [
    {
      "path": "src/auth/middleware.ts",
      "start_line": 1,
      "end_line": 24
    }
  ]
}
```

---

### `POST /api/evaluate`

Run RAG evaluation metrics on a question. Slower than `/api/query` — intended for pipeline quality testing only.

**Request:**

```json
{
  "question": "How does authentication work?",
  "repo": "owner/repo",
  "expected_answer": "optional ground truth for precision/recall",
  "candidate_k": 20,
  "final_k": 5
}
```

**Response:**

```json
{
  "question": "How does authentication work?",
  "answer": "Authentication uses bearer tokens...",
  "passed": true,
  "metrics": [
    {
      "name": "Answer Relevancy",
      "score": 0.95,
      "threshold": 0.7,
      "passed": true,
      "reason": "The answer directly addresses the question."
    },
    {
      "name": "Faithfulness",
      "score": 1.0,
      "threshold": 0.7,
      "passed": true,
      "reason": "All claims are grounded in the retrieved chunks."
    }
  ],
  "confident_link": "https://app.confident-ai.com/..."
}
```

> `ContextualPrecision` and `ContextualRecall` are only evaluated when `expected_answer` is provided.

---

## Environment Variables

| Variable                | Required    | Description                                           |
| ----------------------- | ----------- | ----------------------------------------------------- |
| `QDRANT_URL`            | Yes         | Qdrant Cloud cluster URL                              |
| `QDRANT_API_KEY`        | Yes         | Qdrant Cloud API key                                  |
| `GOOGLE_API_KEY`        | Yes         | Google AI Studio key for Gemini                       |
| `REDIS_URL`             | Yes         | Redis connection URL                                  |
| `EMBEDDING_SERVICE_URL` | Yes         | URL of the embedding service                          |
| `GITHUB_TOKEN`          | Recommended | GitHub PAT — raises rate limit from 60 to 5000 req/hr |
| `CONFIDENT_API_KEY`     | Optional    | Confident AI key for tracing dashboard                |

---

## Roadmap

- [ ] Streaming LLM responses (Server-Sent Events)
- [ ] Metadata filtering by file path or language at query time
- [ ] Support for private repositories
- [ ] Switch to `BAAI/bge-base-en-v1.5` for better code embedding quality
- [ ] tree-sitter upgrade to v0.23+ with individual language packages
