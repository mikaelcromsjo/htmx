# events.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Column, Integer, String, DateTime, JSON, select
from sqlalchemy.orm import Session, declarative_base
from typing import Optional
from datetime import datetime

from app.database import get_db   # <- assumes you have database.py with SessionLocal & engine
from app.templates import templates  # <- assumes you have Jinja2Templates configured


from app.database import engine
from app.models.base import Base
from app.models.models import Event

router = APIRouter(prefix="/events", tags=["events"])



# -----------------------------
# List Events (HTMX fragment)
# -----------------------------
@router.get("/", response_class=HTMLResponse, name="events.list")
def list_events(
    request: Request,
    filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = select(Event)
    if filter:
        query = query.where(Event.name.contains(filter))
    events = db.execute(query).scalars().all()
    return templates.TemplateResponse(
        "events/list.html", {"request": request, "events": events}
    )


# -----------------------------
# Event Detail Modal (HTMX fragment)
# -----------------------------
@router.get("/{event_id}", response_class=HTMLResponse)
def event_detail(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return templates.TemplateResponse(
        "events/modal.html", {"request": request, "event": event, "editable": False}
    )


# -----------------------------
# Edit Event Modal (HTMX fragment)
# -----------------------------
@router.get("/{event_id}/edit", response_class=HTMLResponse)
def edit_event(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return templates.TemplateResponse(
        "events/modal.html", {"request": request, "event": event, "editable": True}
    )


# -----------------------------
# Update Existing Event
# -----------------------------
@router.post("/{event_id}/update", response_class=HTMLResponse)
def update_event(
    request: Request,
    event_id: int,
    name: str = Form(...),
    description: str = Form(None),
    startDate: datetime = Form(...),
    endDate: datetime = Form(...),
    type: str = Form(None),
    extra: str = Form(None),
    db: Session = Depends(get_db),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Update fields
    event.name = name
    event.description = description
    event.startDate = startDate
    event.endDate = endDate
    event.type = type
    if extra:
        import json

        try:
            event.extra = json.loads(extra)
        except Exception:
            event.extra = {"raw": extra}

    db.add(event)
    db.commit()
    db.refresh(event)

    # Re-render updated list
    events = db.execute(select(Event)).scalars().all()
    return templates.TemplateResponse(
        "events/list.html", {"request": request, "events": events}
    )


# -----------------------------
# Create New Event
# -----------------------------
@router.post("/create", response_class=HTMLResponse)
def create_event(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    startDate: datetime = Form(...),
    endDate: datetime = Form(...),
    type: str = Form(None),
    extra: str = Form(None),
    db: Session = Depends(get_db),
):
    import json

    new_event = Event(
        name=name,
        description=description,
        startDate=startDate,
        endDate=endDate,
        type=type,
        extra=None,
    )

    if extra:
        try:
            new_event.extra = json.loads(extra)
        except Exception:
            new_event.extra = {"raw": extra}

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    # Re-render updated list
    events = db.execute(select(Event)).scalars().all()
    return templates.TemplateResponse(
        "events/list.html", {"request": request, "events": events}
    )
