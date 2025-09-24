# events.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi import APIRouter, Depends, Form, Request, HTTPException, Query

from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Column, Integer, String, DateTime, JSON, select
from sqlalchemy.orm import Session, declarative_base
from typing import Optional
from datetime import datetime


from typing import List, Optional
from core.models.base import Base
from pydantic import BaseModel
from pydantic import BaseModel, Field

from datetime import datetime

from core.database import get_db   
from templates import templates
from core.database import engine
from core.models.base import Base
from models.models import Event, EventUpdate
from models.models import Update
from core.functions.helpers import populate

router = APIRouter(prefix="/events", tags=["events"])

# -----------------------------
# List Events (HTMX fragment)
# -----------------------------
@router.get("/", response_class=HTMLResponse, name="events_list")
def events_list(
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
@router.get("event/{event_id}", response_class=HTMLResponse)
def event_detail(
    request: Request,
    event_id: int,
    list: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    
    # Capture all query parameters as a dict
    query_params = dict(request.query_params)

    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if list == "short":
        # Render short template
        return templates.TemplateResponse(
            "events/info.html",
            {
                "request": request, 
                "event": event, 
            }
        )
    else:
        # Render full template
        return templates.TemplateResponse(
            "events/edit.html", {"request": request, "event": event, "editable": True}
        )
     




# -----------------------------
# Update Existing Event
# -----------------------------

@router.post("/event", name="upsert_event", response_class=HTMLResponse)
async def upsert_event(
    request: Request,
    update_data: Update,
    db: Session = Depends(get_db),
):

    # Determine if this is an update or create
    event_id = update_data.model_dump().get("id")
    if event_id:
        try:
            event_id_int = int(event_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event ID")
        event = db.query(Event).filter(Event.id == event_id_int).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
    else:
        event = Event()

    print(update_data.model_dump())

    # Populate DB model dynamically
    event = populate(update_data.model_dump(exclude_unset=True), event, EventUpdate)

    db.add(event)
    db.commit()
    db.refresh(event)

    # Render updated list (HTMX swap)
    events = db.query(Event).all()
    return templates.TemplateResponse(
        "events/list.html",
        {"request": request, "events": events},
    )



# DELETE event
@router.post("/delete/{event_id}", name="delete_event")
def delete_event(event_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    db.delete(event)
    db.commit()
    return {"detail": f"Event {event.name} deleted successfully"}

