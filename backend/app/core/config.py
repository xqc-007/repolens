from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    app_name: str = "RepoLens"
    app_environment: Literal["development", "test", "production"] = "development"
    app_debug: bool = False
    repository_mode: Literal["demo", "github"] = "demo"
    llm_mode: Literal["mock", "real"] = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    github_token: str | None = None
    database_path: str = str(PROJECT_ROOT / "backend" / "repolens.db")
    workspace_root: str = str(PROJECT_ROOT / "workspaces")
    demo_repo_path: str = str(PROJECT_ROOT / "demo_repo")
    max_file_bytes: int = 180_000
    max_context_chars: int = 45_000
    test_timeout_seconds: int = 45
    allowed_test_commands: str = "pytest,npm test,npm run test"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_test_command_list(self) -> list[str]:
        return [x.strip() for x in self.allowed_test_commands.split(",") if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
