from pydantic import BaseModel
from enum import Enum
from deepeval.evaluate.types import EvaluationResult

class IndexRequest(BaseModel):
    repo_url: str        # e.g. "https://github.com/kVarunkk/GetHired"
    branch: str = "main"

class IndexStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

class IndexProgress(BaseModel):
    total_files: int = 0
    fetched_files: int = 0
    chunked_files: int = 0
    embedded_chunks: int = 0
    stored_chunks: int = 0

class IndexStatusResponse(BaseModel):
    job_id: str
    status: IndexStatus
    message: str | None = None
    progress: IndexProgress | None = None

class QueryRequest(BaseModel):
    question: str
    repo: str            # e.g. "kVarunkk/GetHired"
    candidate_k: int = 20
    final_k: int = 5

class QueryResponse(BaseModel):
    answer: str | None
    citations: list[dict]  # list of {path, start_line, end_line}

class EvaluateRequest(BaseModel):
    question: str
    repo: str
    expected_answer: str | None = None
    candidate_k: int = 20
    final_k: int = 5

class MetricResult(BaseModel):
    name: str
    score: float | None
    threshold: float
    passed: bool
    reason: str | None = None

class EvaluateResponse(BaseModel):
    question: str
    answer: str
    passed: bool
    metrics: list[MetricResult]
    confident_link: str | None = None