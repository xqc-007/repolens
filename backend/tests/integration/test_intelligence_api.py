from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_repository_index_api_returns_demo_intelligence():
    response = client.get("/api/repositories/demo/index?force=true")
    assert response.status_code == 200
    body = response.json()
    assert body["repository_id"] == "demo"
    assert body["symbol_count"] >= 3
    assert "Python" in body["languages"]


def test_symbol_search_api_finds_login():
    response = client.get("/api/repositories/demo/symbols", params={"q": "login"})
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["matches"]]
    assert "login" in names


def test_dependency_api_reports_reverse_dependency():
    response = client.get(
        "/api/repositories/demo/dependencies",
        params={"path": "backend/auth.py"},
    )
    assert response.status_code == 200
    assert "backend/api.py" in response.json()["imported_by"]
