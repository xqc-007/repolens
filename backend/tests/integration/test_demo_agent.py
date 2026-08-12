import time
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_demo_agent_finds_login_mismatch():
    r=client.post("/api/agent/runs",json={"repository_id":"demo","question":"Why is login failing?"}); assert r.status_code==200
    run_id=r.json()["id"]
    for _ in range(30):
        data=client.get(f"/api/agent/runs/{run_id}").json()
        if data["status"] in {"completed","failed"}: break
        time.sleep(.05)
    assert data["status"]=="completed"
    assert "mismatch" in data["answer"]["summary"].lower()


def test_demo_change_proposes_patch_and_tests_pass():
    r=client.post("/api/agent/runs",json={"repository_id":"demo","question":"Fix the login bug and show me the diff"})
    run_id=r.json()["id"]
    for _ in range(30):
        data=client.get(f"/api/agent/runs/{run_id}").json()
        if data["status"] in {"completed","failed"}: break
        time.sleep(.05)
    assert data["status"]=="completed"
    assert data["patch"] is not None
    result=client.post(f"/api/agent/runs/{run_id}/tests",json={"command":"pytest","apply_patch":True})
    assert result.status_code==200
    assert result.json()["status"]=="passed"
