# GitHub RAG App

A production-grade **Retrieval-Augmented Generation (RAG)** system that lets you ask questions about any GitHub repository and get accurate answers with file and line number citations.

Built as a portfolio project to demonstrate AI engineering, Python backend development, and production RAG pipeline design.

---

## How It Works

1. Paste a GitHub repo URL — the app fetches all code files via the GitHub API
2. Files are parsed using **tree-sitter** (AST-aware chunking by function/class boundaries)
3. Each chunk is embedded using both **dense** (semantic) and **sparse** (keyword) vectors
4. Vectors are stored in **Qdrant** with repo-level isolation
5. When you ask a question, hybrid search retrieves the most relevant chunks
6. A **cross-encoder re-ranker** re-scores the results for precision
7. **Gemini** generates an answer grounded strictly in the retrieved chunks, with citations

---

## Features

**AST-aware chunking**
Uses tree-sitter to split code at function and class boundaries rather than arbitrary line counts. Supports TypeScript, JavaScript, Python, Go, Rust, Java, C, and C++.

**Hybrid search**
Combines dense vector search (semantic similarity) with sparse BM42 keyword search, fused via Reciprocal Rank Fusion (RRF). Catches both meaning-level and exact-match queries like function names.

**Cross-encoder re-ranking**
After retrieval, a `cross-encoder/ms-marco-MiniLM-L-6-v2` model re-scores candidates by reading the question and each chunk together — significantly improving result precision.

**Multi-repo support**
All repos are indexed in a single Qdrant collection, isolated by a `repo` payload field with a keyword index. Each query is scoped to the repo you specify.

**Async pipeline**
Built on FastAPI with full async support. CPU-bound work (embedding, re-ranking) runs in threadpool executors. Network I/O (GitHub API, Qdrant, Gemini) is fully async.

**Background indexing**
`POST /api/index` returns immediately with a `job_id`. Indexing runs as a background task. Poll `GET /api/index/{job_id}` for status.

**Tracing**
Every request is traced end-to-end using DeepEval's `@observe` decorator — agent → retriever → reranker → LLM — visible in the Confident AI dashboard.

**RAG evaluation**
Pipeline evaluated using DeepEval with faithfulness, answer relevancy, contextual precision, and contextual recall metrics.

---

## Tech Stack

| Layer             | Technology                                            |
| ----------------- | ----------------------------------------------------- |
| Backend           | FastAPI (Python)                                      |
| Vector DB         | Qdrant Cloud                                          |
| Dense embeddings  | `all-MiniLM-L6-v2` (sentence-transformers)            |
| Sparse embeddings | `Qdrant/bm42-all-minilm-l6-v2-attentions` (fastembed) |
| Re-ranking        | `cross-encoder/ms-marco-MiniLM-L-6-v2`                |
| AST parsing       | tree-sitter + tree-sitter-language-pack               |
| LLM               | Gemini 2.5 Flash (Google AI Studio)                   |
| Tracing           | DeepEval + Confident AI                               |
| HTTP client       | httpx (async)                                         |
| Frontend          | Next.js (coming soon)                                 |

---

## Project Structure

```
gh-rag-app/
├── server/
│   ├── main.py               # FastAPI app, lifespan, routes
│   ├── constants.py          # Extensions, node types, config
│   ├── requirements.txt
│   ├── .env
│   ├── core/
│   │   ├── clients.py        # Qdrant, Gemini, embedding models
│   │   ├── fetcher.py        # GitHub API — fetch repo file tree
│   │   ├── chunker.py        # tree-sitter AST chunking
│   │   ├── embedder.py       # Dense + sparse embeddings (parallel)
│   │   ├── retriever.py      # Hybrid search, reranking, ask()
│   │   ├── generator.py      # Prompt building + Gemini call
│   │   └── indexer.py        # Full indexing pipeline
│   └── api/
│       ├── models.py         # Pydantic request/response models
│       └── routes/
│           ├── index.py      # POST /api/index, GET /api/index/{job_id}
│           └── query.py      # POST /api/query
└── client/                   # Next.js frontend (coming soon)
```

---

## Setup

### Prerequisites

- Python 3.11+
- A [Qdrant Cloud](https://cloud.qdrant.io) account (free tier works)
- A [Google AI Studio](https://aistudio.google.com) API key
- A [Confident AI](https://app.confident-ai.com) account for tracing (optional)
- A GitHub personal access token (optional but recommended for higher rate limits)

### 1. Clone the repo

```bash
git clone https://github.com/your-username/gh-rag-app.git
cd gh-rag-app/server
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the `server/` directory:

```env
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
GOOGLE_API_KEY=your-ai-studio-api-key
GITHUB_TOKEN=your-github-personal-access-token
CONFIDENT_API_KEY=your-confident-ai-api-key
```

| Variable            | Required    | Description                                           |
| ------------------- | ----------- | ----------------------------------------------------- |
| `QDRANT_URL`        | Yes         | Your Qdrant Cloud cluster URL                         |
| `QDRANT_API_KEY`    | Yes         | Qdrant Cloud API key                                  |
| `GOOGLE_API_KEY`    | Yes         | Google AI Studio API key for Gemini                   |
| `GITHUB_TOKEN`      | Recommended | GitHub PAT — raises rate limit from 60 to 5000 req/hr |
| `CONFIDENT_API_KEY` | Optional    | Confident AI key for tracing dashboard                |

### 5. Start the server

```bash
uvicorn main:app --reload
```

Server runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.

---

## API Reference

### `POST /api/index`

Start indexing a GitHub repository.

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
  "message": "Indexing started for owner/repo"
}
```

---

### `GET /api/index/{job_id}`

Poll indexing status.

**Response:**

```json
{
  "job_id": "uuid",
  "status": "done",
  "message": "Successfully indexed owner/repo"
}
```

Status values: `pending` | `running` | `done` | `failed`

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
  "answer": "Authentication uses bearer tokens validated by...",
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

### `GET /health`

```json
{ "status": "ok" }
```

---

## Roadmap

- [ ] Next.js frontend with chat UI and clickable citation cards
- [ ] Streaming LLM responses
- [ ] Idempotent re-indexing (skip unchanged files using content hashing)
- [ ] Metadata filtering by file path or language
- [ ] Support for private repositories
