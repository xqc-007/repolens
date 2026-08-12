from app.services.indexing import RepositoryIndexService


def test_demo_repository_index_extracts_languages_symbols_and_dependencies():
    index = RepositoryIndexService().build("demo", force=True)

    assert index.file_count >= 4
    assert index.indexed_file_count >= 4
    assert index.languages["Python"] >= 3
    assert index.languages["TypeScript"] >= 1
    assert index.symbol_count >= 3

    names = {symbol.name for file in index.files for symbol in file.symbols}
    assert "login" in names
    assert "submitLogin" in names


def test_symbol_search_prefers_matching_symbol():
    matches = RepositoryIndexService().search_symbols("demo", "login")

    assert matches
    assert matches[0].name.lower() == "login"


def test_dependency_report_resolves_local_python_import():
    report = RepositoryIndexService().dependency_report("demo", "backend/api.py")

    assert any(item.module == "backend.auth" for item in report.imports)
    assert any(item.resolved_path == "backend/auth.py" for item in report.imports)


def test_dependency_report_finds_reverse_imports():
    report = RepositoryIndexService().dependency_report("demo", "backend/auth.py")

    assert "backend/api.py" in report.imported_by
