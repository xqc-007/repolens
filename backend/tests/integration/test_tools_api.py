from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_tool_catalogue_exposes_permission_boundaries():
    response = client.get("/api/tools")
    assert response.status_code == 200
    tools = {item["name"]: item for item in response.json()["tools"]}
    assert tools["repository_tree"]["permission"] == "read"
    assert tools["validate_patch"]["permission"] == "propose"
    assert tools["run_tests"]["permission"] == "execute"
    assert tools["run_tests"]["requires_explicit_approval"] is True
    assert tools["github_write"]["permission"] == "write"
    assert tools["github_write"]["enabled"] is False
