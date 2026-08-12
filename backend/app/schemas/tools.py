from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agent import TaskType, ToolPermission


class ToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RepositoryTreeArgs(ToolArgs):
    max_files: int = Field(default=1200, ge=1, le=5000)


class SearchCodeArgs(ToolArgs):
    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=20, ge=1, le=50)


class ReadFileArgs(ToolArgs):
    relative: str = Field(min_length=1, max_length=1000)
    max_chars: int | None = Field(default=None, ge=1, le=200_000)


class DependencyArgs(ToolArgs):
    relative: str = Field(min_length=1, max_length=1000)


class ValidatePatchArgs(ToolArgs):
    diff: str = Field(min_length=1, max_length=250_000)
    allowed_files: list[str] = Field(min_length=1, max_length=50)


class RunTestsArgs(ToolArgs):
    command: str = Field(min_length=1, max_length=500)
    diff: str | None = Field(default=None, max_length=250_000)


class WritePlaceholderArgs(ToolArgs):
    message: str = Field(default="", max_length=500)


class ToolExecutionContext(BaseModel):
    repository_id: str
    run_id: str | None = None
    task_type: TaskType = TaskType.EXPLAIN
    approved_permissions: set[ToolPermission] = Field(default_factory=set)
    explicit_execution_approval: bool = False


class ToolDescriptor(BaseModel):
    name: str
    permission: ToolPermission
    description: str
    enabled: bool = True
    requires_explicit_approval: bool = False


class ToolExecutionResult(BaseModel):
    tool: str
    permission: ToolPermission
    status: str
    result: Any | None = None
