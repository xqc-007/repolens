from app.agents.orchestrator import AgentLimits, AgentOrchestrator
from app.schemas.agent import AgentRuntimeState, TaskType, ToolCall


def test_non_read_tool_is_denied_inside_investigation_loop():
    orchestrator = AgentOrchestrator()
    state = AgentRuntimeState(
        repository_id='demo',
        question='push this',
        task_type=TaskType.CHANGE,
    )
    observation = orchestrator._execute_read_call(
        'not-persisted',
        state,
        ToolCall(tool='github_write', arguments={'message': 'push'}, reason='malicious request'),
    )
    assert observation.status == 'denied'
    assert 'READ tools only' in observation.summary


def test_step_and_file_budgets_are_small_and_finite():
    limits = AgentLimits()
    assert 1 <= limits.max_steps <= 8
    assert 1 <= limits.max_files_read <= 12
    assert limits.max_observation_chars <= 18000
