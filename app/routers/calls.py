# app/routers/calls.py

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.database import get_db
from app import models
from app.main import templates  # Jinja2Templates instance

router = APIRouter(
    prefix="/calls",
    tags=["calls"],
)


# ---------------------------
# Dashboard View
# ---------------------------
@router.get("/dashboard", response_class=HTMLResponse, name="calls.dashboard")
def call_center_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Render the main call center dashboard.
    """
    # Example: you might load some stats here
    total_calls = db.query(models.Call).count()
    total_events = db.query(models.CustomerEvent).count()

    return templates.TemplateResponse(
        "calls/dashboard.html",
        {
            "request": request,
            "total_calls": total_calls,
            "total_events": total_events,
        },
    )


# ---------------------------
# Select a Customer for Call Center
# ---------------------------
@router.get("/select/{customer_id}", response_class=HTMLResponse)
def select_customer(customer_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Select a customer (e.g., open their detail view in dashboard).
    """
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        return HTMLResponse("<div>Customer not found</div>", status_code=404)

    return templates.TemplateResponse(
        "calls/customer_detail.html",
        {"request": request, "customer": customer},
    )


# ---------------------------
# Customer Info Fragment
# ---------------------------
@router.get("/customer/{customer_id}/info", response_class=HTMLResponse)
def customer_info(customer_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Return HTMX fragment with customer details.
    """
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        return HTMLResponse("<div>Customer not found</div>", status_code=404)

    return templates.TemplateResponse(
        "calls/fragments/customer_info.html",
        {"request": request, "customer": customer},
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


# ---------------------------
# Event Info Fragment
# ---------------------------
@router.get("/event/{event_id}/info", response_class=HTMLResponse)
def event_info(event_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Return HTMX fragment with details of a specific event.
    """
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        return HTMLResponse("<div>Event not found</div>", status_code=404)

    return templates.TemplateResponse(
        "calls/fragments/event_info.html",
        {"request": request, "event": event},
    )


# ---------------------------
# Update Customer Event Relation
# ---------------------------
@router.post("/customer/{customer_id}/event/{event_id}/update", response_class=HTMLResponse)
def update_customer_event_relation(
    customer_id: int,
    event_id: int,
    request: Request,
    status: str = Form(...),
    visited: Optional[bool] = Form(False),
    db: Session = Depends(get_db),
):
    """
    Update the relation between a customer and an event.
    """
    relation = (
        db.query(models.CustomerEvent)
        .filter(
            models.CustomerEvent.customerId == customer_id,
            models.CustomerEvent.eventId == event_id,
        )
        .first()
    )

    if not relation:
        return HTMLResponse("<div>Relation not found</div>", status_code=404)

    relation.status = status
    relation.visited = visited
    db.commit()
    db.refresh(relation)

    return templates.TemplateResponse(
        "calls/fragments/customer_event_detail.html",
        {"request": request, "relation": relation},
    )
