# app/routers/calls.py

from fastapi import APIRouter, Depends, Request, Form, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from core.database import get_db
from templates import templates


from models.models import Customer, Call, Event, Caller
from core.functions.helpers import render
from functions.customers import get_selected_ids, get_customers, SelectedIDs


router = APIRouter(prefix="/calls", tags=["calls"])

# Create Caller
@router.post("/admin/callers")
def create_caller(name: str, db: Session = Depends(get_db)):
    caller = Caller(name=name)
    db.add(caller)
    db.commit()
    db.refresh(caller)
    return caller

# List Callers
@router.get("/admin/callers")
def list_callers(db: Session = Depends(get_db)):
    return db.query(Caller).all()

# Delete Caller
@router.delete("/admin/callers/{caller_id}")
def delete_caller(caller_id: int, db: Session = Depends(get_db)):
    caller = db.query(Caller).get(caller_id)
    if not caller:
        raise HTTPException(status_code=404, detail="Caller not found")
    db.delete(caller)
    db.commit()
    return {"status": "deleted", "caller_id": caller_id}