# app/routers/calls.py

from fastapi import APIRouter, Depends, Request, Form, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.templates import templates


from app.models.models import Customer, Call, Event, EventCustomer, Caller
from app.functions.helpers import render
from app.functions.customers import get_selected_ids, get_customers, SelectedIDs

from app.data.constants import categories_map, organisations_map, personalities_map
from app.auth import get_current_user



router = APIRouter(prefix="/calls", tags=["calls"])



# ---------------------------
# Dashboard View
# ---------------------------



@router.api_route("/dashboard", methods=["GET", "POST"], response_class=HTMLResponse, name="calls_dashboard")
def call_center_dashboard(
    request: Request,
    selected_ids: Optional[SelectedIDs] = None,
    db: Session = Depends(get_db),
):
    """
    Single route to render the call center dashboard for both GET and POST.
    """
    ids = get_selected_ids(request, selected_ids)
    customers = get_customers(db, ids)
    query = db.query(Call)
    calls = query.all()
    query = db.query(Event)
    events = query.all()

    return render(
        "calls/dashboard.html",
        {"request": request, "customers": customers, "calls": calls, "events": events }, 
    )



# -----------------------------
# Customer Details and call list (HTMX fragment)
# -----------------------------

from sqlalchemy import desc
from ..state import user_data, active_connections

@router.get("/customer_data", name="customer_data", response_class=HTMLResponse)
async def customer_data(
    request: Request,
    customer_id: str = Query(default="0", alias="customer_id"),
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    

    customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")


    user_data.setdefault(user, {})["name"] = customer.first_name + " " + customer.last_name
    user_data.setdefault(user, {})["number"] = customer.phone
    # Broadcast to all connected receivers

    to_remove = []
    for ws in active_connections.get(user, []):
        try:
            await ws.send_json(user_data[user])
        except RuntimeError:
            # WebSocket is closed, mark for removal
            to_remove.append(ws)

    for ws in to_remove:
        active_connections[user].remove(ws)


    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id)
        .first()
    )
    
    callers = (
        db.query(Caller)
        .all()
    )    

    calls = db.query(Call).filter(Call.customer_id == int(customer_id)).order_by(desc(Call.id)).all()
    return templates.TemplateResponse(
        "calls/details_calls.html",
        {
            "request": request, 
            "customer": customer,
            "categories_map": categories_map,
            "organisations_map": organisations_map, 
            "personalities_map": personalities_map, 
            "callers": callers,
            "customer": customer,
            "calls": calls
        }
    )


# -----------------------------
# List Calls (HTMX fragment)
# -----------------------------


@router.get("/customer/{customer_id}", response_class=HTMLResponse)
def customer_calls(
    request: Request,
    customer_id: str,
    list: str | None = Query(default=None),
    db: Session = Depends(get_db)
):
    print("List calls")    
    # Capture all query parameters as a dict
    query_params = dict(request.query_params)

    calls = db.query(Call).filter(Call.caller_id == int(customer_id)).all()

    return templates.TemplateResponse(
        "calls/call_log.html",
        {"request": request, "calls": calls},
    )

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


## Get number to call

@router.get("/number", response_class=HTMLResponse, name="number")
def number(
    request: Request,
    filter: Optional[str] = None,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    
    return templates.TemplateResponse(
        "calls/number.html", {"request": request, "user": user}
    )



# ---------------------------
# Call Details
# ---------------------------


@router.get("/call/{call_id}", response_class=HTMLResponse)
def call_details(
    request: Request,
    call_id: str,
    db: Session = Depends(get_db)
):
    
    call = db.query(Call).filter(Call.id == int(call_id)).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    call = (
        db.query(Call)
        .filter(Call.id == call_id)
        .first()
    )

    return templates.TemplateResponse(
        "calls/info.html",
        {
            "request": request, 
            "call": call, 
            "call_id": call_id, 
        }
    )


# ---------------------------
# Update Customer Call Data
# ---------------------------

from app.models.models import Update
from app.models.models import Call, CallUpdate
from app.functions.helpers import populate
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

@router.post("/call/save", name="save_call", response_class=HTMLResponse)
async def save_call(
    request: Request,
    update_data: Update,
    comment: str | None = Query(None),
    db: Session = Depends(get_db),
):
    
    # update event status
    event_id = update_data.event_id
    if (event_id > 0):
        event_status = update_data.event_status
    customer_id = update_data.customer_id


    # Get the CustomerEvent match
    event_customer = db.query(EventCustomer).filter_by(
        customer_id=customer_id, event_id=event_id
    ).first()

    # Check if event_customer exists
    if not event_customer:
        print("No existing EventCustomer found. Creating a new one.")
        event_customer = EventCustomer(
            customer_id=customer_id,
            event_id=event_id
        )
    else:
        print("Found existing EventCustomer:", event_customer)

    # Update status
    event_customer.status = event_status
    print("Setting EventCustomer.status =", event_status)

    # Add to DB and commit
    db.add(event_customer)
    try:
        db.commit()
        print("Database commit successful.")
    except Exception as e:
        db.rollback()
        print("Database commit failed:", e)

    # Try to fetch existing call by ID if provided
    existing_call = None
    call_id = update_data.id if hasattr(update_data, "id") else None
    if isinstance(call_id, str):
        existing_call = db.query(Call).filter_by(id=call_id).first()

    # Use existing call or create new one
    call = existing_call or Call()

    # Populate DB model dynamically
    try:
        call = populate(update_data.model_dump(exclude_unset=True), call, CallUpdate)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    # Set call_date for new calls
    if not existing_call:
        call.call_date = datetime.now()
        call.id = None  # let DB auto-generate if using Integer PK        
        db.add(call)


    #TODO add caller id
    call.caller_id = 1

    try:
        db.commit()
        db.refresh(call)
    except IntegrityError:
        db.rollback()
        raise

    return JSONResponse(content={"detail": "Call saved successfully", "call_id": call.id})

# Autogenerated

# ---------------------------
# Select a Customer for Call Center
# ---------------------------
@router.get("/select/{customer_id}", response_class=HTMLResponse)
def select_customer(customer_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Select a customer (e.g., open their detail view in dashboard).

    """

    customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()
    if not customer:
        return HTMLResponse("<div>Customer not found</div>", status_code=404)

    return templates.TemplateResponse(
        "calls/customer_detail.html",
        {"request": request, "customer": customer},
    )


# ---------------------------
# Customer Info Fragment
# ---------------------------
@router.get("/customer/{customer_id}/info", response_class=HTMLResponse, name="calls.customer_info")
def customer_info(customer_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Return HTMX fragment with customer details.
    """
    customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()
    if not customer:
        return HTMLResponse("<div>Customer not found</div>", status_code=404)

    return templates.TemplateResponse(
        "calls/customer_info.html",
        {"request": request, "customer": customer},
    )

# ---------------------------
# Call Info Fragment
# ---------------------------
@router.get("/calls/{call_id}/info", response_class=HTMLResponse, name="calls.call_info")
def call_info(call_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Return HTMX fragment with call details.
    """
    call = db.query(Call).filter(Call.id == int(call_id)).first()
    if not call:
        return HTMLResponse("<div>Customer not found</div>", status_code=404)

    return templates.TemplateResponse(
        "calls/call_info.html",
        {"request": request, "call": call},
    )


# ---------------------------
# Customer Call Log Fragment
# ---------------------------
@router.get("/customer/{customer_id}/calls", response_class=HTMLResponse)
def customer_call_log(customer_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Return HTMX fragment with a customer's call history.
    """
    calls = (
        db.query(models.Call)
        .filter(models.Call.customer_id == customer_id)
        .order_by(models.Call.timestamp.desc())
        .all()
    )

    return templates.TemplateResponse(
        "calls/fragments/customer_calls.html",
        {"request": request, "calls": calls, "customer_id": customer_id},
    )


# ---------------------------
# List Customer Events Fragment
# ---------------------------
@router.get("/customer/{customer_id}/events", response_class=HTMLResponse)
def list_customer_events(customer_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Return HTMX fragment with all events associated with a customer.
    """
    events = (
        db.query(models.CustomerEvent)
        .filter(models.CustomerEvent.customerId == customer_id)
        .all()
    )

    return templates.TemplateResponse(
        "calls/fragments/customer_events.html",
        {"request": request, "events": events, "customer_id": customer_id},
    )


# -----------------------------
# Event Detail Modal (HTMX fragment)
# -----------------------------
@router.get("/event/{event_id}", response_class=HTMLResponse)
def calls_event_detail(
    request: Request,
    event_id: int,
    customer_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    # Debug: print input values
    print("Debug: customer_id =", customer_id)
    print("Debug: event_id =", event_id)

    # Get the EventCustomer match
    event_customer = db.query(EventCustomer).filter_by(
        customer_id=customer_id, event_id=event_id
    ).first()

    # Debug: print query result
    print("Debug: event_customer =", event_customer)

    event_status = None
    if event_customer:
        event_status = event_customer.status

    return templates.TemplateResponse(
        "calls/event_info.html",
        {
            "request": request, 
            "event": event, 
            "event_status": event_status,
        }
    )
     
