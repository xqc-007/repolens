from fastapi import APIRouter, HTTPException, Query

from app.schemas.retrieval import RetrievalResponse
from app.services.retrieval import RetrievalService

router = APIRouter(prefix="/repositories", tags=["Repository retrieval"])
retrieval = RetrievalService()


@router.get("/{repository_id}/retrieve", response_model=RetrievalResponse)
def retrieve_repository_context(
    repository_id: str,
    q: str = Query(min_length=1, max_length=500),
    max_candidates: int = Query(default=10, ge=1, le=30),
    max_files: int = Query(default=6, ge=1, le=12),
):
    try:
        return retrieval.retrieve(
            repository_id,
            q,
            max_candidates=max_candidates,
            max_files=max_files,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
