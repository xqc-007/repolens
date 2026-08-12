from pathlib import Path
import pytest
from app.services.security import safe_resolve, redact_secrets

def test_safe_resolve_blocks_escape(tmp_path:Path):
    with pytest.raises(ValueError): safe_resolve(tmp_path,"../../.env")

def test_secret_redaction():
    text,n=redact_secrets("api_key=supersecretvalue")
    assert "supersecretvalue" not in text and n>=1
