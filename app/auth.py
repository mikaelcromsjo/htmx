from fastapi import FastAPI, Request
from fastapi import FastAPI, Request, Depends, HTTPException


# Dependency to check if user is authenticated
def get_current_user(request: Request):
    if not request.session.get("authenticated"):

        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.session.get("user")
