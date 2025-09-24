from fastapi import FastAPI, Request
from fastapi import FastAPI, Request, Depends, HTTPException

from sqlalchemy.orm import relationship, Session
from fastapi import FastAPI, Request, Form, Depends, HTTPException

from app.core.models.models import User
from app.core.models.models import BaseMixin, Update, User
from app.core.database import get_db


# --- Helper ---
def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    username = request.session.get("user")
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user