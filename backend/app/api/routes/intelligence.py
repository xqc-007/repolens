from fastapi import APIRouter, HTTPException, Query

from app.schemas.intelligence import (
    DependencyReport,
    RepositoryIndex,
    SymbolSearchResponse,
)
from app.services.indexing import RepositoryIndexService

router = APIRouter(prefix="/repositories", tags=["Repository intelligence"])
indexer = RepositoryIndexService()


@router.get("/{repository_id}/index", response_model=RepositoryIndex)
def repository_index(repository_id: str, force: bool = Query(default=False)):
    try:
        return indexer.build(repository_id, force=force)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{repository_id}/symbols", response_model=SymbolSearchResponse)
def search_symbols(repository_id: str, q: str = Query(min_length=1, max_length=200)):
    try:
        return SymbolSearchResponse(query=q, matches=indexer.search_symbols(repository_id, q))
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{repository_id}/dependencies", response_model=DependencyReport)
def dependencies(repository_id: str, path: str = Query(min_length=1, max_length=1000)):
    try:
        return indexer.dependency_report(repository_id, path)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
