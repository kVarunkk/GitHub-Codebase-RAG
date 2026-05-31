from pydantic import BaseModel
from enum import Enum

class IndexRequest(BaseModel):
    repo_url: str        # e.g. "https://github.com/kVarunkk/GetHired"
    branch: str = "main"

class IndexStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

class IndexStatusResponse(BaseModel):
    job_id: str
    status: IndexStatus
    message: str | None = None

class QueryRequest(BaseModel):
    question: str
    repo: str            # e.g. "kVarunkk/GetHired"
    candidate_k: int = 20
    final_k: int = 5

class QueryResponse(BaseModel):
    answer: str | None
    citations: list[dict]  # list of {path, start_line, end_line}