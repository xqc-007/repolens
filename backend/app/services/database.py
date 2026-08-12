import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings


_SENSITIVE_AUDIT_KEYS = {
    "content",
    "diff",
    "token",
    "api_key",
    "github_token",
    "openai_api_key",
    "password",
    "secret",
}


def _audit_safe(value: Any, key: str | None = None) -> Any:
    """Produce a small metadata-only audit representation.

    Audit logs prove what capability was requested without persisting repository code,
    generated patches, credentials, or other high-risk payloads.
    """
    if key and key.lower() in _SENSITIVE_AUDIT_KEYS:
        if isinstance(value, str):
            return f"[REDACTED:{len(value)} chars]"
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _audit_safe(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_audit_safe(v) for v in list(value)[:50]]
    if isinstance(value, str) and len(value) > 500:
        return value[:200] + f"… [TRUNCATED:{len(value)} chars]"
    return value


class Database:
    def __init__(self):
        self.path = Path(get_settings().database_path)
        self.lock = threading.Lock()
        self._init()

    def _conn(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    def _init(self):
        with self._conn() as c:
            c.executescript(
                '''
                CREATE TABLE IF NOT EXISTS agent_runs(id TEXT PRIMARY KEY, repository_id TEXT, question TEXT, status TEXT, answer_json TEXT, patch_json TEXT, error TEXT, created_at TEXT, updated_at TEXT);
                CREATE TABLE IF NOT EXISTS agent_events(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, event_type TEXT, message TEXT, created_at TEXT);
                CREATE TABLE IF NOT EXISTS tool_audit_logs(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, tool_name TEXT, permission TEXT, arguments_json TEXT, status TEXT, created_at TEXT);
                '''
            )

    def create_run(self, id, repo, q):
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            c.execute(
                "INSERT INTO agent_runs VALUES(?,?,?,?,?,?,?,?,?)",
                (id, repo, q, "queued", None, None, None, now, now),
            )

    def update_run(self, id, **fields):
        if not fields:
            return
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [id]
        with self._conn() as c:
            c.execute(f"UPDATE agent_runs SET {sets} WHERE id=?", vals)

    def get_run(self, id):
        with self._conn() as c:
            r = c.execute("SELECT * FROM agent_runs WHERE id=?", (id,)).fetchone()
        return dict(r) if r else None

    def event(self, run_id, event_type, message):
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            c.execute(
                "INSERT INTO agent_events(run_id,event_type,message,created_at) VALUES(?,?,?,?)",
                (run_id, event_type, message, now),
            )

    def events(self, run_id, after=0):
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM agent_events WHERE run_id=? AND id>? ORDER BY id",
                (run_id, after),
            ).fetchall()
        return [dict(r) for r in rows]

    def audits(self, run_id):
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM tool_audit_logs WHERE run_id=? ORDER BY id", (run_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def audit(self, run_id, tool, permission, args, status):
        now = datetime.now(timezone.utc).isoformat()
        safe = _audit_safe(args)
        with self._conn() as c:
            c.execute(
                "INSERT INTO tool_audit_logs(run_id,tool_name,permission,arguments_json,status,created_at) VALUES(?,?,?,?,?,?)",
                (run_id, tool, permission, json.dumps(safe, default=str)[:4000], status, now),
            )
