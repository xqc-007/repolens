USERS={"demo@example.com":"correct-horse"}
def login(email:str,password:str)->bool:
    return USERS.get(email)==password
