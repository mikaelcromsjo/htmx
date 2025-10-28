# admin.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi import APIRouter, Depends, Form, Request, HTTPException, Query

from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Column, Integer, String, DateTime, JSON, select
from sqlalchemy.orm import Session, declarative_base
from typing import Optional
from datetime import datetime
from datetime import date
from sqlalchemy import select, and_
from datetime import date, timedelta
from core.auth import get_current_user

from typing import List, Optional
from core.models.base import Base
from pydantic import BaseModel
from pydantic import BaseModel, Field

from datetime import datetime

from core.database import get_db   
from templates import templates
from core.database import engine
from core.models.base import Base
from models.models import Update
from core.functions.helpers import populate

router = APIRouter(prefix="/admin", tags=["admin"])

# -----------------------------
# List Dashboard (HTMX fragment)
# -----------------------------
@router.get("/", response_class=HTMLResponse, name="admin_dashboard")
def admin_dashboard(
    request: Request,
    filter: Optional[str] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    
    return templates.TemplateResponse(
        "admin/dashboard.html", {"request": request, "user": user}
    )