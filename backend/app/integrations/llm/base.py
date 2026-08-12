from typing import Protocol

from app.schemas.agent import (
    AgentAnswer,
    AgentObservation,
    AgentPlan,
    AgentStepDecision,
    PatchProposal,
)


class LLMProvider(Protocol):
    def plan(self, question: str, tree: list[str], tools: list[dict]) -> AgentPlan: ...

    def next_action(
        self,
        question: str,
        plan: AgentPlan,
        observations: list[AgentObservation],
        tools: list[dict],
        *,
        step: int,
        max_steps: int,
        files_read: list[str],
    ) -> AgentStepDecision: ...

    def answer(self, question: str, context: list[dict]) -> AgentAnswer: ...

    def patch(self, question: str, context: list[dict]) -> PatchProposal: ...
