from app.services.retrieval import RetrievalService


def test_query_terms_expand_authentication_language():
    terms = RetrievalService().query_terms("Why is login failing?")
    assert "login" in terms
    assert "auth" in terms
    assert "authentication" in terms


def test_ranked_retrieval_finds_login_flow_files():
    result = RetrievalService().retrieve("demo", "Why is login failing?")
    paths = [item.path for item in result.candidates[:5]]

    assert "frontend/src/LoginForm.tsx" in paths
    assert "backend/auth.py" in paths
    assert "backend/api.py" in paths
    assert result.context
    assert result.context_chars <= 45000


def test_dependency_expansion_surfaces_imported_backend_file():
    result = RetrievalService().retrieve("demo", "login_endpoint")
    paths = [item.path for item in result.candidates]
    assert "backend/api.py" in paths
    assert "backend/auth.py" in paths


def test_context_is_bounded_and_contains_line_numbers():
    result = RetrievalService().retrieve("demo", "login", max_files=2)
    assert len(result.context) <= 2
    assert all(":" in chunk.content for chunk in result.context)
    assert result.context_chars == sum(len(chunk.content) for chunk in result.context)
