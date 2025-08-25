from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.orm import Session, declarative_base
from typing import List, Optional, Dict, Any
from app.models.models import Customer
from sqlalchemy.orm import Session, joinedload
from app.models.base import Base

from app.database import get_db
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel


# -------------------------------------------------
# Router & Templates Setup
# -------------------------------------------------
router = APIRouter(prefix="/customers", tags=["customers"])
templates = Jinja2Templates(directory="app/templates")



# -------------------------------------------------
# List Customers
# Returns an HTMX fragment with list.html
# -------------------------------------------------
@router.get("/", response_class=HTMLResponse, name="customers.list")
def list_customers(
    request: Request,
    filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Customer)
    if filter:
        query = query.filter(Customer.name.ilike(f"%{filter}%"))
    customers = query.all()
    return templates.TemplateResponse(
        "customers/list.html",
        {"request": request, "customers": customers, "filter": filter},
    )


# -------------------------------------------------
# Customer Detail
# Returns customers/edit.html
# -------------------------------------------------
@router.get("/{customer_id}", response_class=HTMLResponse)
@router.get("/new", response_class=HTMLResponse) 
def customer_detail(
    request: Request,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db)
):

    if customer_id is not None:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
    else:
        # Creating a new customer (empty/default object)
        customer = Customer()    
    customer = (
        db.query(Customer)
        .options(joinedload(Customer.alarms))  # eager load alarms
        .filter(Customer.id == customer_id)
        .first()
    )

    # Example categories dictionary (replace with your actual JSON source)
    categories = {
        "Category1": ["Sub1", "Sub2"],
        "Category2": ["SubA", "SubB"],
    }

    # Example personality types list
    personality_types = ["Type1", "Type2", "Type3", "Type4", "Type5", "Type6"]

    return templates.TemplateResponse(
        "customers/edit.html",
        {
            "request": request, "customer": 
            customer, "mode": "edit",
            "categories": categories,
            "personality_types": personality_types, 
        }
    )



# -------------------------------------------------
# Update Customer
# Processes form submission and updates DB
# -------------------------------------------------
from typing import List, Optional
from app.models.base import Base

class CustomerUpdate(BaseModel):
    name: str
    user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    comment: Optional[str] = None
    sub_caller: Optional[str] = None
    organisation: Optional[str] = None
    personalityType: Optional[List[str]] = []
    categories: Optional[List[str]] = []
    tags: Optional[str] = None

@router.post("/{customer_id}/update", response_class=HTMLResponse, response_model=None)
def update_customer(
    request: Request,
    customer_update: CustomerUpdate,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    
    if customer_id is not None:
        # Fetch customer
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
    else:
        customer = Customer()    

    # Update fields dynamically
    for field, value in customer_update.dict(exclude_unset=True).items():
        if field == "tags" and value is not None:
            setattr(customer, field, [t.strip() for t in value.split(",") if t.strip()])
        else:
            setattr(customer, field, value)

    db.commit()
    db.refresh(customer)

    # Render updated list (HTMX swap)
    customers = db.query(Customer).all()
    return templates.TemplateResponse(
        "customers/list.html", {"request": request, "customers": customers}
    )

