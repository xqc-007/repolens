"""Deterministic RepoLens evaluation runner for the bundled demo repository.

This harness complements pytest. It evaluates end-to-end agent behaviour, retrieval quality,
patch scope and security-facing tool usage against labelled cases.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services.database import Database  # noqa: E402

client = TestClient(app)
db = Database()


def _wait_for_run(run_id: str) -> dict:
    run: dict = {}
    for _ in range(120):
        run = client.get(f"/api/agent/runs/{run_id}").json()
        if run["status"] in {"completed", "failed"}:
            return run
        time.sleep(0.03)
    return run


def _run_case(case: dict) -> dict:
    created = client.post(
        "/api/agent/runs",
        json={"repository_id": "demo", "question": case["question"]},
    )
    created.raise_for_status()
    run_id = created.json()["id"]
    run = _wait_for_run(run_id)

    answer = run.get("answer") or {}
    files = {item["path"] for item in answer.get("files", [])}
    expected = set(case.get("expected_files", []))
    forbidden = set(case.get("forbidden_files", []))
    recall = len(files & expected) / len(expected) if expected else 1.0
    minimum_recall = float(case.get("minimum_retrieval_recall", 0.5))
    forbidden_hits = sorted(files & forbidden)

    patch = run.get("patch") or {}
    affected = set(patch.get("affected_files", []))
    allowed_patch = set(case.get("allowed_patch_files", []))
    forbidden_patch = set(case.get("forbidden_patch_files", []))
    patch_scope_ok = True
    if allowed_patch:
        patch_scope_ok = affected.issubset(allowed_patch)
    if affected & forbidden_patch:
        patch_scope_ok = False

    audits = db.audits(run_id)
    permissions = {row["permission"] for row in audits}
    security = case.get("security_expectations", {})
    security_ok = True
    if security.get("write_tools_disabled") and "write" in permissions:
        security_ok = False
    if security.get("execute_requires_approval") and "execute" in permissions:
        # No eval case sends explicit execution approval, so execution must not occur here.
        security_ok = False

    passed = (
        run.get("status") == "completed"
        and recall >= minimum_recall
        and not forbidden_hits
        and patch_scope_ok
        and security_ok
    )

    return {
        "case": case["id"],
        "passed": passed,
        "status": run.get("status"),
        "retrieval_recall": round(recall, 2),
        "files": sorted(files),
        "forbidden_file_hits": forbidden_hits,
        "patch_files": sorted(affected),
        "patch_scope_ok": patch_scope_ok,
        "tool_permissions_observed": sorted(permissions),
        "security_ok": security_ok,
    }


def main() -> None:
    cases = sorted((ROOT / "evals" / "cases").glob("*.json"))
    results = [_run_case(json.loads(path.read_text())) for path in cases]
    summary = {
        "cases": len(results),
        "passed": sum(1 for item in results if item["passed"]),
        "failed": sum(1 for item in results if not item["passed"]),
        "results": results,
    }
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
