import os
import shutil
import subprocess
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.integrations.github import GitHubClient
from app.services.security import is_allowed_path, safe_resolve, sanitize_repository_content


class WorkspaceService:
    def __init__(self):
        self.settings = get_settings()
        self.workspace_root = Path(self.settings.workspace_root).resolve()
        self.demo_repo = Path(self.settings.demo_repo_path).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def get_repo_path(self, repository_id: str) -> Path:
        if repository_id == "demo":
            return self.demo_repo
        path = self.workspace_root / repository_id
        if not path.exists():
            raise FileNotFoundError("Repository not found")
        return path

    def _clone(self, url: str, branch: str, env: dict[str, str], askpass_path: str | None = None) -> tuple[str, Path]:
        repo_id = uuid.uuid4().hex[:12]
        target = self.workspace_root / repo_id
        cmd = ["git", "clone", "--depth", "1", "--branch", branch, url, str(target)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90, env=env)
        finally:
            if askpass_path:
                Path(askpass_path).unlink(missing_ok=True)
        if result.returncode != 0:
            shutil.rmtree(target, ignore_errors=True)
            error = (result.stderr or result.stdout or "Git clone failed").strip()
            # Never echo credentials if Git includes a URL in an error.
            if "@github.com" in error:
                error = "GitHub clone failed. Check repository access, token permissions, and branch name."
            raise RuntimeError(error)
        return repo_id, target

    def clone_public_repo(self, url: str, branch: str = "main") -> tuple[str, Path]:
        if not (url.startswith("https://github.com/") or url.startswith("http://github.com/")):
            raise ValueError("Only GitHub HTTPS repository URLs are supported")
        env = {k: v for k, v in os.environ.items() if k not in {"GITHUB_TOKEN", "OPENAI_API_KEY"}}
        env["GIT_TERMINAL_PROMPT"] = "0"
        return self._clone(url, branch, env)

    def clone_github_repo(self, full_name: str, branch: str | None = None) -> tuple[str, Path, str]:
        github = GitHubClient()
        if not github.configured:
            raise RuntimeError("GitHub is not configured. Add GITHUB_TOKEN to backend/.env")
        full_name = github.validate_full_name(full_name)
        selected_branch = branch or "main"
        if branch is None:
            repos = github.list_repositories()
            match = next((repo for repo in repos if repo["full_name"].lower() == full_name.lower()), None)
            if match:
                selected_branch = match["default_branch"]
        env, askpass_path = github.authenticated_clone_environment()
        url = f"https://github.com/{full_name}.git"
        repo_id, path = self._clone(url, selected_branch, env, askpass_path)
        return repo_id, path, selected_branch

    def copy_for_execution(self, repository_id: str) -> Path:
        source = self.get_repo_path(repository_id)
        target = self.workspace_root / f"exec-{uuid.uuid4().hex[:12]}"
        shutil.copytree(source, target, ignore=shutil.ignore_patterns(".git", "node_modules", ".venv", "__pycache__"))
        return target

    def tree(self, repository_id: str, max_files: int = 1200) -> list[str]:
        root = self.get_repo_path(repository_id)
        files = []
        for p in root.rglob("*"):
            if p.is_file() and is_allowed_path(p.relative_to(root)):
                files.append(p.relative_to(root).as_posix())
                if len(files) >= max_files:
                    break
        return sorted(files)

    def read_file(self, repository_id: str, relative: str, max_chars: int | None = None) -> str:
        root = self.get_repo_path(repository_id)
        path = safe_resolve(root, relative)
        rel = path.relative_to(root)
        if not is_allowed_path(rel):
            raise ValueError("File is excluded by security policy")
        if not path.is_file():
            raise FileNotFoundError(relative)
        if path.stat().st_size > self.settings.max_file_bytes:
            raise ValueError("File exceeds size limit")
        raw = path.read_text(errors="replace")
        raw = raw[: max_chars or self.settings.max_context_chars]
        safe, _, _ = sanitize_repository_content(raw)
        return safe
