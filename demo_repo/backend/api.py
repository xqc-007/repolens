from backend.auth import login

def login_endpoint(payload:dict)->dict:
    email=payload.get("email")
    password=payload.get("password")
    if not email or not password:
        return {"ok":False,"error":"email and password are required"}
    return {"ok":login(email,password)}
