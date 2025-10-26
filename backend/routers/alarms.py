# alarms.py
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

from typing import List, Optional
from core.models.base import Base
from pydantic import BaseModel
from pydantic import BaseModel, Field

from datetime import datetime

from core.database import get_db   
from templates import templates
from core.database import engine
from core.models.base import Base
from models.models import Alarm
from models.models import Update
from core.functions.helpers import populate

router = APIRouter(prefix="/alarms", tags=["alarms"])

# -----------------------------
# List Alarms (HTMX fragment)
# -----------------------------
@router.get("/", response_class=HTMLResponse, name="alarms_list")
def alarms_list(
    request: Request,
    filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = select(Alarm)
    if filter:
        query = query.where(Alarm.name.contains(filter))
    alarms = db.execute(query).scalars().all()
    return templates.TemplateResponse(
        "alarms/list.html", {"request": request, "alarms": alarms}
    )



# -----------------------------
# Alarm Detail Modal (HTMX fragment)
# -----------------------------
@router.get("/new", name="new_alarm", response_class=HTMLResponse)
def new_alarm(
    request: Request,
    db: Session = Depends(get_db),
):
    alarm = Alarm.empty()

    return templates.TemplateResponse(
        "alarms/edit.html", {"request": request, "alarm": alarm, "editable": True}
    )               

# -----------------------------
# Alarm Detail Modal (HTMX fragment)
# -----------------------------
@router.get("/alarm/{alarm_id}", response_class=HTMLResponse)
def alarm_detail(
    request: Request,
    alarm_id: int,
    list: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    

    alarm = db.get(Alarm, alarm_id)
    if not alarm:
        alarm = Alarm().empty()
    
    if list == "short":
        # Render short template
        return templates.TemplateResponse(
            "alarms/info.html",
            {
                "request": request, 
                "alarm": alarm, 
            }
        )
    else:
        # Render full template
        return templates.TemplateResponse(
            "alarms/edit.html", {"request": request, "alarm": alarm, "editable": True}
        )
     




# DELETE alarm
@router.post("/delete/{alarm_id}", name="delete_alarm")
def delete_alarm(alarm_id: str, db: Session = Depends(get_db)):
    alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    db.delete(alarm)
    db.commit()
    return {"detail": f"Alarm deleted successfully"}

@router.post("/set_filter", name="set_filter", response_class=HTMLResponse)
async def set_filter(
    request: Request,
    db: Session = Depends(get_db),
):
    data = await request.json()

    start_str = data.get("alarm_date_filter-start")
    end_str = data.get("alarm_date_filter-end")

    alarm_date_filter_start = date.fromisoformat(start_str) if start_str else None
    alarm_date_filter_end = date.fromisoformat(end_str) + timedelta(days=1) if end_str else None

    query = select(Alarm)

    if alarm_date_filter_start and alarm_date_filter_end:
        query = query.where(
            Alarm.start_date >= alarm_date_filter_start,
            Alarm.start_date < alarm_date_filter_end
        )
    elif alarm_date_filter_start:
        query = query.where(Alarm.start_date >= alarm_date_filter_start)
    elif alarm_date_filter_end:
        query = query.where(Alarm.start_date < alarm_date_filter_end)
    # else: no filter, return all alarms

    alarms = db.execute(query).scalars().all()

    return templates.TemplateResponse(
        "alarms/list.html",
        {"request": request, "alarms": alarms}
    )