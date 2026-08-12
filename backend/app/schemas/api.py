from pydantic import BaseModel, Field
from app.schemas.agent import AgentAnswer, PatchProposal


class RepositoryInfo(BaseModel):
    id: str
    name: str
    source: str
    branch: str
    path: str
    languages: list[str] = Field(default_factory=list)
    file_count: int = 0


class ConnectRepositoryRequest(BaseModel):
    url: str
    branch: str = "main"


class ConnectGitHubRepositoryRequest(BaseModel):
    full_name: str
    branch: str | None = None


class GitHubStatus(BaseModel):
    configured: bool
    connected: bool
    login: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    error: str | None = None


class GitHubRepository(BaseModel):
    id: int | None = None
    name: str
    full_name: str
    private: bool = False
    default_branch: str = "main"
    language: str | None = None
    updated_at: str | None = None
    html_url: str | None = None


class AskRequest(BaseModel):
    repository_id: str = "demo"
    question: str = Field(min_length=3, max_length=4000)


class AgentRunResponse(BaseModel):
    id: str
    status: str
    question: str
    answer: AgentAnswer | None = None
    patch: PatchProposal | None = None
    error: str | None = None


class TestRunRequest(BaseModel):
    command: str
    apply_patch: bool = True


class TestRunResponse(BaseModel):
    status: str
    command: str
    exit_code: int
    duration_ms: int
    output_summary: str
