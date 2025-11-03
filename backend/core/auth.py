from fastapi import FastAPI, Request
from fastapi import FastAPI, Request, Depends, HTTPException

from sqlalchemy.orm import relationship, Session
from fastapi import FastAPI, Request, Form, Depends, HTTPException

from core.models.models import User
from core.models.models import BaseMixin, Update, User
from core.database import get_db


# --- Helper ---
def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user")

    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user