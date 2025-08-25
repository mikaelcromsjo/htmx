# app/routers/alarms.py

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.database import get_db  # your session dependency
from app.models.models import Customer, Event 
from app.models.base import Base
from fastapi.templating import Jinja2Templates
from app.models.models import Alarm

# ------------------------------------------------------
# Templates
# ------------------------------------------------------
templates = Jinja2Templates(directory="app/templates")



# ------------------------------------------------------
# Router
# ------------------------------------------------------
router = APIRouter(prefix="/alarms", tags=["alarms"])


# ------------------------------------------------------
# List Alarms → HTMX fragment
# ------------------------------------------------------
@router.get("/list", response_class=HTMLResponse, name="alarms.list")
def list_alarms(request: Request, db: Session = Depends(get_db)):
    alarms: List[Alarm] = db.query(Alarm).order_by(Alarm.timestamp.desc()).all()
    return templates.TemplateResponse(
        "alarms/list.html",
        {"request": request, "alarms": alarms},
    )


# ------------------------------------------------------
# Create Alarm → HTMX fragment
# ------------------------------------------------------
@router.post("/create", response_class=HTMLResponse)
def create_alarm(
    request: Request,
    customerId: int = Form(...),
    eventId: int = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    new_alarm = Alarm(
        customerId=customerId,
        eventId=eventId,
        note=note,
        timestamp=datetime.utcnow(),
    )
    db.add(new_alarm)
    db.commit()
    db.refresh(new_alarm)

    # Re-render alarms list fragment
    alarms: List[Alarm] = db.query(Alarm).order_by(Alarm.timestamp.desc()).all()
    return templates.TemplateResponse(
        "alarms/list.html",
        {"request": request, "alarms": alarms},
    )


# ------------------------------------------------------
# Delete Alarm → HTMX fragment
# ------------------------------------------------------
@router.post("/delete/{alarm_id}", response_class=HTMLResponse)
def delete_alarm(alarm_id: int, request: Request, db: Session = Depends(get_db)):
    alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()
    if alarm:
        db.delete(alarm)
        db.commit()

    # Re-render alarms list fragment
    alarms: List[Alarm] = db.query(Alarm).order_by(Alarm.timestamp.desc()).all()
    return templates.TemplateResponse(
        "alarms/list.html",
        {"request": request, "alarms": alarms},
    )
