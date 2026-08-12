import os
import stat
import tempfile
from pathlib import Path

import httpx

from app.core.config import get_settings


class GitHubClient:
    API_BASE = "https://api.github.com"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.token = self.settings.github_token

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "RepoLens/0.2",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method: str, path: str, **kwargs):
        try:
            with httpx.Client(timeout=20.0, headers=self._headers()) as client:
                response = client.request(method, f"{self.API_BASE}{path}", **kwargs)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Could not reach GitHub: {exc}") from exc

        if response.status_code == 401:
            raise RuntimeError("GitHub token was rejected. Check GITHUB_TOKEN in backend/.env.")
        if response.status_code == 403:
            raise RuntimeError("GitHub denied this request. Check token repository access and permissions.")
        if response.status_code >= 400:
            message = response.json().get("message", "GitHub request failed") if response.content else "GitHub request failed"
            raise RuntimeError(message)
        return response

    def profile(self) -> dict:
        if not self.token:
            raise RuntimeError("GitHub is not configured")
        data = self._request("GET", "/user").json()
        return {
            "login": data.get("login"),
            "avatar_url": data.get("avatar_url"),
            "name": data.get("name"),
        }

    def list_repositories(self, limit: int = 100) -> list[dict]:
        if not self.token:
            raise RuntimeError("GitHub is not configured")
        response = self._request(
            "GET",
            "/user/repos",
            params={
                "per_page": min(limit, 100),
                "sort": "updated",
                "direction": "desc",
                "affiliation": "owner,collaborator,organization_member",
            },
        )
        repos = []
        for item in response.json():
            repos.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "full_name": item.get("full_name"),
                    "private": bool(item.get("private")),
                    "default_branch": item.get("default_branch") or "main",
                    "language": item.get("language"),
                    "updated_at": item.get("updated_at"),
                    "html_url": item.get("html_url"),
                }
            )
        return repos

    @staticmethod
    def validate_full_name(full_name: str) -> str:
        value = full_name.strip().strip("/")
        parts = value.split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("Repository must be in owner/name format")
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
        if any(any(ch not in allowed for ch in part) for part in parts):
            raise ValueError("Repository owner/name contains unsupported characters")
        return value

    def authenticated_clone_environment(self) -> tuple[dict[str, str], str | None]:
        """Return a git environment plus a temporary askpass script path.

        The token is passed through an environment variable rather than embedded in
        the clone URL or subprocess command line. The caller must delete the script.
        """
        env = {k: v for k, v in os.environ.items() if k not in {"OPENAI_API_KEY"}}
        env["GIT_TERMINAL_PROMPT"] = "0"
        if not self.token:
            env.pop("GITHUB_TOKEN", None)
            return env, None

        fd, script_path = tempfile.mkstemp(prefix="repolens-git-askpass-", suffix=".sh")
        os.close(fd)
        Path(script_path).write_text(
            '#!/bin/sh\n'
            'case "$1" in\n'
            '  *Username*) echo "x-access-token" ;;\n'
            '  *Password*) printf "%s" "$REPOLENS_GITHUB_TOKEN" ;;\n'
            'esac\n'
        )
        os.chmod(script_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        env["GIT_ASKPASS"] = script_path
        env["REPOLENS_GITHUB_TOKEN"] = self.token
        env.pop("GITHUB_TOKEN", None)
        return env, script_path
