from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.integrations.github import GitHubClient
from app.schemas.api import (
    ConnectGitHubRepositoryRequest,
    ConnectRepositoryRequest,
    GitHubRepository,
    GitHubStatus,
    RepositoryInfo,
)
from app.services.workspace import WorkspaceService

router = APIRouter(prefix="/repositories", tags=["Repositories"])
ws = WorkspaceService()


def info(repo_id, path, source, branch="main"):
    tree = ws.tree(repo_id)
    exts = sorted({Path(p).suffix.lstrip(".") for p in tree if Path(p).suffix})
    return RepositoryInfo(
        id=repo_id,
        name=Path(path).name,
        source=source,
        branch=branch,
        path=str(path),
        languages=exts[:12],
        file_count=len(tree),
    )


@router.get("/demo", response_model=RepositoryInfo)
def demo():
    return info("demo", ws.get_repo_path("demo"), "demo")


@router.get("/github/status", response_model=GitHubStatus)
def github_status():
    github = GitHubClient()
    if not github.configured:
        return GitHubStatus(configured=False, connected=False)
    try:
        profile = github.profile()
        return GitHubStatus(configured=True, connected=True, **profile)
    except Exception as exc:
        return GitHubStatus(configured=True, connected=False, error=str(exc))


@router.get("/github", response_model=list[GitHubRepository])
def github_repositories():
    try:
        return GitHubClient().list_repositories()
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/github/connect", response_model=RepositoryInfo)
def connect_github(req: ConnectGitHubRepositoryRequest):
    try:
        rid, path, branch = ws.clone_github_repo(req.full_name, req.branch)
        result = info(rid, path, "github", branch)
        result.name = req.full_name
        return result
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{repository_id}/tree")
def tree(repository_id: str):
    try:
        return {"files": ws.tree(repository_id)}
    except Exception as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/connect", response_model=RepositoryInfo)
def connect(req: ConnectRepositoryRequest):
    try:
        rid, path = ws.clone_public_repo(req.url, req.branch)
        return info(rid, path, "github", req.branch)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
