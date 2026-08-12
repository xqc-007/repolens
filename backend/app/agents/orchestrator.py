from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from app.integrations.llm.provider import get_llm_provider
from app.schemas.agent import (
    AgentObservation,
    AgentRuntimeState,
    AgentDecisionType,
    ToolCall,
    ToolPermission,
)
from app.schemas.tools import ToolExecutionContext
from app.services.database import Database
from app.services.patches import PatchService
from app.services.retrieval import RetrievalService
from app.services.workspace import WorkspaceService
from app.tools.registry import ToolRegistry


@dataclass(frozen=True)
class AgentLimits:
    max_steps: int = 8
    max_files_read: int = 12
    max_observation_chars: int = 18000


class AgentOrchestrator:
    def __init__(self, limits: AgentLimits | None = None):
        self.db = Database()
        self.workspace = WorkspaceService()
        self.retrieval = RetrievalService(self.workspace)
        self.tools = ToolRegistry(self.db)
        self.patches = PatchService()
        self.limits = limits or AgentLimits()

    def start(self, repository_id: str, question: str) -> str:
        run_id = uuid.uuid4().hex
        self.db.create_run(run_id, repository_id, question)
        return run_id

    @staticmethod
    def _normalise_result(value: Any, max_chars: int = 18000) -> Any:
        if isinstance(value, list):
            out = []
            for item in value[:30]:
                if hasattr(item, "path"):
                    out.append(
                        {
                            "path": getattr(item, "path", None),
                            "line": getattr(item, "line", None),
                            "snippet": getattr(item, "snippet", None),
                            "score": getattr(item, "score", None),
                        }
                    )
                elif hasattr(item, "model_dump"):
                    out.append(item.model_dump(mode="json"))
                else:
                    out.append(item)
            return out
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, str):
            return value[:max_chars] + ("\n[TRUNCATED]" if len(value) > max_chars else "")
        if isinstance(value, dict):
            return value
        return value

    @staticmethod
    def _call_key(call: ToolCall) -> str:
        return json.dumps(
            {"tool": call.tool, "arguments": call.arguments},
            sort_keys=True,
            default=str,
        )

    def _execute_read_call(self, run_id: str, state: AgentRuntimeState, call: ToolCall) -> AgentObservation:
        state.step_count += 1
        if call.tool == "read_file":
            relative = str(call.arguments.get("relative", ""))
            if relative and relative not in state.files_read:
                if len(state.files_read) >= state.max_files_read:
                    return AgentObservation(
                        step=state.step_count,
                        tool=call.tool,
                        arguments=call.arguments,
                        status="denied",
                        summary="File-read budget reached",
                    )
                state.files_read.append(relative)

        tool = self.tools.tools.get(call.tool)
        if not tool or tool.permission is not ToolPermission.READ:
            return AgentObservation(
                step=state.step_count,
                tool=call.tool,
                arguments=call.arguments,
                status="denied",
                summary="Investigation phase permits READ tools only",
            )

        self.db.event(run_id, "tool_started", call.reason)
        try:
            tool_result = self.tools.execute(
                call.tool,
                ToolExecutionContext(
                    repository_id=state.repository_id,
                    run_id=run_id,
                    task_type=state.task_type,
                    approved_permissions={ToolPermission.READ},
                ),
                call.arguments,
            )
            normalised = self._normalise_result(tool_result.result, self.limits.max_observation_chars)
            self.db.event(run_id, "tool_completed", f"{call.tool.replace('_', ' ').title()} completed")
            return AgentObservation(
                step=state.step_count,
                tool=call.tool,
                arguments=call.arguments,
                status="ok",
                summary=f"{call.tool} completed",
                result=normalised,
            )
        except Exception as exc:
            self.db.event(run_id, "tool_error", f"{call.tool}: {exc}")
            return AgentObservation(
                step=state.step_count,
                tool=call.tool,
                arguments=call.arguments,
                status="error",
                summary=str(exc)[:300],
            )

    def _context_from_observations(self, state: AgentRuntimeState) -> list[dict]:
        context: list[dict] = []
        for obs in state.observations:
            if obs.tool != "read_file" or obs.status != "ok" or not isinstance(obs.result, str):
                continue
            path = obs.arguments.get("relative")
            if not path:
                continue
            context.append(
                {
                    "path": path,
                    "start_line": 1,
                    "end_line": None,
                    "content": obs.result,
                    "reason": "Read by the controlled investigation loop",
                }
            )
        if context:
            return context[:6]
        retrieval = self.retrieval.retrieve(state.repository_id, state.question, max_files=6)
        return [chunk.model_dump(mode="json") for chunk in retrieval.context]

    def execute(self, run_id: str):
        row = self.db.get_run(run_id)
        if not row:
            return
        repo = row["repository_id"]
        question = row["question"]
        try:
            self.db.update_run(run_id, status="running")
            self.db.event(run_id, "status", "Understanding your request…")
            tree = self.workspace.tree(repo)
            self.db.event(run_id, "repository", f"Mapped {len(tree)} repository files")

            llm = get_llm_provider()
            plan = llm.plan(question, tree, self.tools.catalogue())
            self.db.event(run_id, "plan", f"Built a {plan.task_type.value} investigation plan")
            state = AgentRuntimeState(
                repository_id=repo,
                question=question,
                task_type=plan.task_type,
                max_steps=self.limits.max_steps,
                max_files_read=self.limits.max_files_read,
            )

            pending = list(plan.calls[:2])
            while state.step_count < state.max_steps:
                if pending:
                    call = pending.pop(0)
                else:
                    decision = llm.next_action(
                        question,
                        plan,
                        state.observations,
                        self.tools.catalogue(),
                        step=state.step_count,
                        max_steps=state.max_steps,
                        files_read=state.files_read,
                    )
                    self.db.event(run_id, "activity", decision.activity)
                    if decision.action is AgentDecisionType.FINISH:
                        break
                    call = decision.tool_call
                    if call is None:
                        break

                key = self._call_key(call)
                if key in state.executed_call_keys:
                    self.db.event(run_id, "guardrail", f"Skipped repeated {call.tool} request")
                    break
                state.executed_call_keys.add(key)
                observation = self._execute_read_call(run_id, state, call)
                state.observations.append(observation)

            if state.step_count >= state.max_steps:
                self.db.event(run_id, "guardrail", f"Stopped at the {state.max_steps}-step investigation limit")

            context = self._context_from_observations(state)
            self.db.event(run_id, "context", f"Synthesising from {len(context)} bounded evidence regions")
            answer = llm.answer(question, context)

            patch = None
            if plan.task_type.value in {"change", "tests"} and answer.can_propose_patch:
                self.db.event(run_id, "patch", "Preparing a reviewable patch…")
                candidate = llm.patch(question, context)
                if candidate.unified_diff:
                    allowed = [c["path"] for c in context]
                    self.tools.execute(
                        "validate_patch",
                        ToolExecutionContext(
                            repository_id=repo,
                            run_id=run_id,
                            task_type=plan.task_type,
                            approved_permissions={ToolPermission.PROPOSE},
                        ),
                        {"diff": candidate.unified_diff, "allowed_files": allowed},
                    )
                    patch = candidate

            self.db.update_run(
                run_id,
                status="completed",
                answer_json=answer.model_dump_json(),
                patch_json=patch.model_dump_json() if patch else None,
            )
            self.db.event(run_id, "completed", "Analysis complete")
        except Exception as exc:
            self.db.update_run(run_id, status="failed", error=str(exc))
            self.db.event(run_id, "failed", f"Analysis failed: {exc}")
