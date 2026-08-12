from app.agents.orchestrator import AgentLimits, AgentOrchestrator
from app.schemas.agent import AgentPlan, TaskType, ToolCall


def test_call_key_is_stable_for_equivalent_arguments():
    first = ToolCall(tool="search_code", arguments={"query": "login", "limit": 5}, reason="a")
    second = ToolCall(tool="search_code", arguments={"limit": 5, "query": "login"}, reason="b")
    assert AgentOrchestrator._call_key(first) == AgentOrchestrator._call_key(second)


def test_agent_limits_are_bounded():
    limits = AgentLimits()
    assert limits.max_steps <= 8
    assert limits.max_files_read <= 12
