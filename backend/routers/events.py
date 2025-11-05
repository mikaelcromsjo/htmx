# events.py
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
from models.models import Event, EventUpdate, EventCustomer, Customer
from models.models import Update
from core.functions.helpers import populate, local_to_utc

router = APIRouter(prefix="/events", tags=["events"])

# -----------------------------
# List Events (HTMX fragment)
# -----------------------------
@router.get("/", response_class=HTMLResponse, name="events_list")
def events_list(
    request: Request,
    filter: Optional[str] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    query = select(Event)
    if filter:
        query = query.where(Event.name.contains(filter))
    events = db.execute(query).scalars().all()
    return templates.TemplateResponse(
        "events/list.html", {"request": request, "events": events, "is_admin": user.admin,
}
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
@router.get("/event/{event_id}", response_class=HTMLResponse)
def event_detail(
    request: Request,
    event_id: int,
    list: str | None = Query(default=None),
    status_filter: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    

    event = db.get(Event, event_id)
    if not event:
        event = Event().empty()
    
    if list == "short":

    # Query event customers
        query = db.query(EventCustomer).join(Customer).filter(EventCustomer.event_id == event_id)
        event_customers = query.all()

        # Calculate totals per status
        totals = {"not_going":0, "maybe":0, "going":0, "paid":0, "attended":0}
        for ec in event_customers:
            if ec.status == 2:
                totals["not_going"] += 1
            elif ec.status == 1:
                totals["maybe"] += 1
            elif ec.status == 3:
                totals["going"] += 1
            elif ec.status == 4:
                totals["paid"] += 1
            elif ec.status == 5:
                totals["attended"] += 1

        
        if status_filter is not None:
            query = query.filter(EventCustomer.status == status_filter)        
        else:
            status_filter = 0
        event_customers = query.all()


        # Render short template
        return templates.TemplateResponse(
            "events/info.html",
            {
                "request": request, 
                "event": event, 
                "event_customers": event_customers,
                "totals": totals,
                "status_filter": status_filter
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

@router.post("/event/upsert", name="upsert_event", response_class=HTMLResponse)
async def upsert_event(
    request: Request,
    update_data: Update,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    
    print (update_data.model_dump())
    if not user.admin:
        raise HTTPException(status_code=401, detail="Error. Only Admin can edit events")
    
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
        event = Event().empty()


    data_dict = update_data.model_dump(exclude_unset=True)

    # Ensure 'extra' exists and is a dict
    if 'extra' not in data_dict or not isinstance(data_dict['extra'], dict):
        data_dict['extra'] = {}

    # Move any keys that start with "extra." into the extra dict
    for key, value in list(data_dict.items()):
        if key.startswith("extra."):
            field_name = key.split(".", 1)[1]  # remove "extra."
            data_dict['extra'][field_name] = value
            del data_dict[key]  # optionally clean up the flat key


    # Populate DB model dynamically
    event = populate(data_dict, event, EventUpdate)

    db.add(event)
    db.commit()
    db.refresh(event)

    # Render updated list (HTMX swap)
    events = db.query(Event).all()
    response = templates.TemplateResponse(
        "events/list.html",
        {"request": request, "events": events},
    )
    # Set the popup message in a custom header
    response.headers["HX-Popup-Message"] = "Saved"
    response.headers["HX-Trigger"] = "dashboardEventsReload"
    return response

# DELETE event
@router.post("/delete/{event_id}", name="delete_event")
def delete_event(event_id: str, db: Session = Depends(get_db), user = Depends(get_current_user)):

    if not user.admin:
        return {"detail": f"Error. Only Admin can delete events"}


    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    db.delete(event)
    db.commit()
    return {"detail": f"Event {event.name} deleted successfully"}

@router.post("/set_filter", name="set_filter", response_class=HTMLResponse)
async def set_filter(
    request: Request,
    db: Session = Depends(get_db),
):
    data = await request.json()

    start_str = data.get("event_date_filter-start")
    end_str = data.get("event_date_filter-end")

    # Convert to UTC-aware datetimes if provided
    event_date_filter_start = local_to_utc(start_str) if start_str else None
    event_date_filter_end = (local_to_utc(end_str) + timedelta(days=1)) if end_str else None
    query = select(Event)

    if event_date_filter_start and event_date_filter_end:
        query = query.where(
            Event.start_date >= event_date_filter_start,
            Event.start_date < event_date_filter_end
        )
    elif event_date_filter_start:
        query = query.where(Event.start_date >= event_date_filter_start)
    elif event_date_filter_end:
        query = query.where(Event.start_date < event_date_filter_end)
    # else: no filter, return all events

    events = db.execute(query).scalars().all()

    return templates.TemplateResponse(
        "events/list.html",
        {"request": request, "events": events}
    )