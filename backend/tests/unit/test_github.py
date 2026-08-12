import pytest

from app.integrations.github import GitHubClient


def test_repository_full_name_validation():
    assert GitHubClient.validate_full_name("openai/openai-python") == "openai/openai-python"


def test_repository_full_name_blocks_invalid_values():
    with pytest.raises(ValueError):
        GitHubClient.validate_full_name("https://github.com/openai/openai-python")
    with pytest.raises(ValueError):
        GitHubClient.validate_full_name("owner/repo/extra")
