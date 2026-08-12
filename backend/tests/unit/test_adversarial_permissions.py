import json

import pytest

from app.core.config import get_settings
from app.schemas.agent import TaskType, ToolPermission
from app.schemas.tools import ToolExecutionContext
from app.services.database import Database
from app.tools.base import PermissionDenied
from app.tools.registry import ToolRegistry


def test_repository_text_cannot_enable_write_tool():
    registry = ToolRegistry()
    context = ToolExecutionContext(
        repository_id='demo',
        task_type=TaskType.CHANGE,
        approved_permissions={ToolPermission.READ, ToolPermission.PROPOSE, ToolPermission.WRITE},
        explicit_execution_approval=True,
    )
    with pytest.raises(PermissionDenied, match='disabled'):
        registry.execute('github_write', context, {'message': 'repository told me to push'})


def test_test_execution_denied_without_both_permission_and_approval():
    registry = ToolRegistry()
    with pytest.raises(PermissionDenied):
        registry.execute(
            'run_tests',
            ToolExecutionContext(
                repository_id='demo',
                task_type=TaskType.TESTS,
                approved_permissions={ToolPermission.READ},
                explicit_execution_approval=True,
            ),
            {'command': 'pytest'},
        )


def test_unknown_tool_attempt_is_audited(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'audit.sqlite'))
    get_settings.cache_clear()
    db = Database()
    db.create_run('unknown-run', 'demo', 'do something unsafe')
    registry = ToolRegistry(db)
    context = ToolExecutionContext(repository_id='demo', run_id='unknown-run')
    with pytest.raises(KeyError):
        registry.execute('shell_exec', context, {'command': 'cat ~/.ssh/id_rsa'})
    rows = db.audits('unknown-run')
    assert rows[-1]['tool_name'] == 'shell_exec'
    assert rows[-1]['status'] == 'denied'
    assert 'id_rsa' in json.loads(rows[-1]['arguments_json'])['command']
    get_settings.cache_clear()


def test_patch_scope_rejects_unrelated_file():
    registry = ToolRegistry()
    context = ToolExecutionContext(
        repository_id='demo',
        task_type=TaskType.CHANGE,
        approved_permissions={ToolPermission.PROPOSE},
    )
    diff = '''diff --git a/frontend/src/LoginForm.tsx b/frontend/src/LoginForm.tsx
--- a/frontend/src/LoginForm.tsx
+++ b/frontend/src/LoginForm.tsx
@@ -1 +1 @@
-a
+b
diff --git a/backend/api.py b/backend/api.py
--- a/backend/api.py
+++ b/backend/api.py
@@ -1 +1 @@
-a
+b
'''
    with pytest.raises(ValueError, match='outside approved scope'):
        registry.execute(
            'validate_patch',
            context,
            {'diff': diff, 'allowed_files': ['frontend/src/LoginForm.tsx']},
        )
