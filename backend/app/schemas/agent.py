from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class TaskType(str, Enum):
    EXPLAIN = "explain"
    DIAGNOSE = "diagnose"
    IMPACT = "impact"
    CHANGE = "change"
    TESTS = "tests"


class ToolPermission(str, Enum):
    READ = "read"
    PROPOSE = "propose"
    EXECUTE = "execute"
    WRITE = "write"


class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str


class AgentPlan(BaseModel):
    goal: str
    task_type: TaskType
    calls: list[ToolCall] = Field(default_factory=list, max_length=8)


class AgentObservation(BaseModel):
    step: int
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: str
    summary: str
    result: Any | None = None


class AgentDecisionType(str, Enum):
    TOOL = "tool"
    FINISH = "finish"


class AgentStepDecision(BaseModel):
    action: AgentDecisionType
    activity: str = Field(min_length=1, max_length=180)
    tool_call: ToolCall | None = None

    @model_validator(mode="after")
    def validate_tool_call(self):
        if self.action is AgentDecisionType.TOOL and self.tool_call is None:
            raise ValueError("tool_call is required when action=tool")
        if self.action is AgentDecisionType.FINISH:
            self.tool_call = None
        return self


class AgentRuntimeState(BaseModel):
    repository_id: str
    question: str
    task_type: TaskType
    step_count: int = 0
    max_steps: int = 8
    files_read: list[str] = Field(default_factory=list)
    max_files_read: int = 12
    observations: list[AgentObservation] = Field(default_factory=list)
    executed_call_keys: set[str] = Field(default_factory=set)


class FileReference(BaseModel):
    path: str
    start_line: int | None = None
    end_line: int | None = None
    reason: str


class Finding(BaseModel):
    title: str
    explanation: str
    evidence: list[FileReference] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class AgentAnswer(BaseModel):
    summary: str
    what_i_found: list[str]
    why: str
    suggested_fix: str | None = None
    impact: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    files: list[FileReference] = Field(default_factory=list)
    can_propose_patch: bool = False


class PatchProposal(BaseModel):
    summary: str
    unified_diff: str
    affected_files: list[str]
    risk_level: str
    confidence: float = Field(ge=0, le=1)
