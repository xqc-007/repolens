from backend.api import login_endpoint

def test_login_contract_uses_email():
    assert login_endpoint({"email":"demo@example.com","password":"correct-horse"}) == {"ok":True}

def test_missing_email_is_rejected():
    result=login_endpoint({"username":"demo@example.com","password":"correct-horse"})
    assert result["ok"] is False
