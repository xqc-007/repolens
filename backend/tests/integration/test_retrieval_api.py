from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_retrieval_api_returns_ranked_candidates_and_context():
    response = client.get(
        "/api/repositories/demo/retrieve",
        params={"q": "Why is login failing?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["repository_id"] == "demo"
    assert body["query_terms"]
    assert body["candidates"]
    assert body["context"]
    paths = [item["path"] for item in body["candidates"]]
    assert "backend/auth.py" in paths
