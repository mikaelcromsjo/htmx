# events.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Column, Integer, String, DateTime, JSON, select
from sqlalchemy.orm import Session, declarative_base
from typing import Optional
from datetime import datetime

from app.database import get_db   
from app.templates import templates


from app.database import engine
from app.models.base import Base
from app.models.models import Event

from typing import List, Optional
from app.models.base import Base
from pydantic import BaseModel
from datetime import datetime

class EventUpdate(BaseModel):
    name: str
    description: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    type: Optional[List[str]] = None

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
@router.get("/new", name="new_event", response_class=HTMLResponse)
def new_event(
    request: Request,
    db: Session = Depends(get_db),
):
    event = Event.empty()

    return templates.TemplateResponse(
        "events/edit.html", {"request": request, "event": event, "editable": True}
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
        "events/edit.html", {"request": request, "event": event, "editable": True}
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
        "events/edit.html", {"request": request, "event": event, "editable": True}
    )


# -----------------------------
# Update Existing Event
# -----------------------------

@router.post("/{event_id}/update", response_class=HTMLResponse)
def update_event(
    request: Request,
    event_update: EventUpdate,
    event_id: str,
    db: Session = Depends(get_db),
):
    
    event = db.query(Event).filter(Event.id == int(event_id)).first()
    if not event:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    event = (
        db.query(Event)
        .filter(Event.id == event_id)
        .first()
    )

    # Update fields dynamically
    for field, value in event_update.model_dump(exclude_unset=True).items():
 #       if field == "tags" and value is not None:
 #           setattr(event, field, [t.strip() for t in value.split(",") if t.strip()])
 #       else:
        setattr(event, field, value)

    db.add(event)
    db.commit()
    db.refresh(event)

    # Render updated list (HTMX swap)
    events = db.query(Event).all()
    return templates.TemplateResponse(
        "events/list.html", {"request": request, "events": events}
    )


@router.post("/create", name="create_event", response_class=HTMLResponse, response_model=None)
def create_event(
    request: Request,
    event_update: EventUpdate,
    db: Session = Depends(get_db),
):
    
    event = Event()

    # Update fields dynamically
    for field, value in event_update.model_dump(exclude_unset=True).items():
 #       if field == "tags" and value is not None:
 #           setattr(event, field, [t.strip() for t in value.split(",") if t.strip()])
 #       else:
        setattr(event, field, value)

#    if not event.endDate:
#        event.endDate = datetime.utcnow() + timedelta(hours=1),

    db.add(event)
    db.commit()
    db.refresh(event)

    # Render updated list (HTMX swap)
    events = db.query(Event).all()
    return templates.TemplateResponse(
        "events/list.html", {"request": request, "events": events}
    )

