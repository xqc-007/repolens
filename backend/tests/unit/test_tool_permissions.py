import pytest

from app.schemas.agent import TaskType, ToolPermission
from app.schemas.tools import ToolExecutionContext
from app.tools.base import PermissionDenied
from app.tools.registry import ToolRegistry


def ctx(**kwargs):
    defaults = dict(repository_id="demo", task_type=TaskType.EXPLAIN)
    defaults.update(kwargs)
    return ToolExecutionContext(**defaults)


def test_read_tool_is_safe_by_default():
    registry = ToolRegistry()
    result = registry.execute("repository_tree", ctx(), {"max_files": 20})
    assert result.status == "ok"
    assert result.permission is ToolPermission.READ
    assert any(path == "backend/auth.py" for path in result.result)


def test_read_file_cannot_escape_repository():
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="escapes repository workspace"):
        registry.execute("read_file", ctx(), {"relative": "../../.env"})


def test_model_cannot_override_repository_scope():
    registry = ToolRegistry()
    with pytest.raises(Exception):
        registry.execute(
            "read_file",
            ctx(repository_id="demo"),
            {"relative": "backend/auth.py", "repository_id": "another-repo"},
        )


def test_propose_denied_for_explanation_task():
    registry = ToolRegistry()
    with pytest.raises(PermissionDenied, match="change or test-generation"):
        registry.execute(
            "validate_patch",
            ctx(approved_permissions={ToolPermission.PROPOSE}),
            {"diff": "--- a/a.py\n+++ b/a.py\n", "allowed_files": ["a.py"]},
        )


def test_execute_requires_explicit_approval():
    registry = ToolRegistry()
    with pytest.raises(PermissionDenied, match="explicit user approval"):
        registry.execute(
            "run_tests",
            ctx(
                task_type=TaskType.TESTS,
                approved_permissions={ToolPermission.EXECUTE},
                explicit_execution_approval=False,
            ),
            {"command": "pytest"},
        )


def test_write_tool_is_disabled_even_when_permission_is_supplied():
    registry = ToolRegistry()
    with pytest.raises(PermissionDenied, match="disabled"):
        registry.execute(
            "github_write",
            ctx(
                task_type=TaskType.CHANGE,
                approved_permissions={ToolPermission.WRITE},
                explicit_execution_approval=True,
            ),
            {"message": "push this"},
        )


def test_audit_log_redacts_diff_payload(tmp_path, monkeypatch):
    from app.core.config import get_settings
    from app.services.database import Database

    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "audit.sqlite"))
    db = Database()
    db.create_run("audit-run", "demo", "fix it")
    registry = ToolRegistry(db)
    diff = "--- a/backend/auth.py\n+++ b/backend/auth.py\n" + ("x" * 800)
    registry.execute(
        "validate_patch",
        ctx(
            run_id="audit-run",
            task_type=TaskType.CHANGE,
            approved_permissions={ToolPermission.PROPOSE},
        ),
        {"diff": diff, "allowed_files": ["backend/auth.py"]},
    )
    rows = db.audits("audit-run")
    assert rows
    assert "[REDACTED:" in rows[-1]["arguments_json"]
    assert ("x" * 100) not in rows[-1]["arguments_json"]
    get_settings.cache_clear()
