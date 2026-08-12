from pydantic import BaseModel, Field


class RetrievalSignal(BaseModel):
    kind: str
    detail: str
    score: float


class RetrievalCandidate(BaseModel):
    path: str
    score: float
    reasons: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    dependency_distance: int | None = None


class ContextChunk(BaseModel):
    path: str
    start_line: int
    end_line: int
    content: str
    reason: str
    score: float
    redactions: int = 0
    security_flags: list[str] = Field(default_factory=list)


class RetrievalResponse(BaseModel):
    repository_id: str
    query: str
    query_terms: list[str] = Field(default_factory=list)
    candidates: list[RetrievalCandidate] = Field(default_factory=list)
    context: list[ContextChunk] = Field(default_factory=list)
    context_chars: int = 0
    truncated: bool = False
