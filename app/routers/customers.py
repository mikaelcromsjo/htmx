from fastapi import APIRouter, Depends, Form, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.orm import Session

from pydantic import BaseModel, Field

from typing import List, Optional, Dict, Any
from typing import Any, Union, Optional, get_origin, get_args

from app.models.base import Base
from app.database import get_db
from app.functions.helpers import render
from app.templates import templates
from app.data.constants import categories, organisations
from app.models.models import Customer, CustomerUpdate, Caller
from app.functions.helpers import populate

from app.models.models import Update


# -------------------------------------------------
# Router & Templates Setup
# -------------------------------------------------
router = APIRouter(prefix="/customers", tags=["customers"])

# -------------------------------------------------
# List Customers
# Returns an HTMX fragment with list.html
# -------------------------------------------------
@router.get("/", response_class=HTMLResponse, name="customers_list")
def customers_list(
    request: Request,
    filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Customer)
    if filter:
        query = query.filter(Customer.name.ilike(f"%{filter}%"))
    customers = query.all()

    return render(
        "customers/list.html",
        {"request": request, 
         "customers": customers, 
         "filter": filter},
    )


# -------------------------------------------------
# Customer Detail
# Returns customers/edit.html
# -------------------------------------------------


@router.get("/new", response_class=HTMLResponse) 
def customer_new(
    request: Request,
    db: Session = Depends(get_db)
):

    customer = Customer.empty()

    query = db.query(Caller)
    callers = query.all()

    return templates.TemplateResponse(
        "customers/edit.html",
        {
            "request": request, 
            "customer": customer, 
            "mode": "edit",
            "categories": categories,
            "callers": callers, 
            "organisations": organisations, 
        }
    )

@router.post("/customer/upsert", name="upsert_customer", response_class=HTMLResponse)
async def upsert_customer(
    request: Request,
    update_data: Update,
    db: Session = Depends(get_db),
):
#    from models import Customer
#    from schemas import CustomerUpdate

    # Determine if this is an update or create
    customer_id = update_data.model_dump().get("id")
    if customer_id:
        try:
            customer_id_int = int(customer_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid customer ID")
        customer = db.query(Customer).filter(Customer.id == customer_id_int).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
    else:
        customer = Customer()
        
    data_dict = update_data.model_dump()

    # --- Temporarily remove relationships before populate ---
    caller_id = data_dict.pop("caller", None)  # remove 'caller' from dict

    # Populate DB model dynamically (everything except relationships)
    customer = populate(data_dict, customer, CustomerUpdate)

    # --- Handle relationships AFTER populate ---
    if isinstance(caller_id, int):
        caller_instance = db.get(Caller, int(caller_id))
        if not caller_instance:
            raise HTTPException(status_code=404, detail="Caller not found")
        customer.caller = caller_instance  # assign the actual SQLAlchemy object


    db.add(customer)
    db.commit()
    db.refresh(customer)

    # Render updated list (HTMX swap)
    customers = db.query(Customer).all()
    return templates.TemplateResponse(
        "customers/list.html",
        {
            "request": request, 
            "customers": customers},
    )





@router.get("/customer/{customer_id}", response_class=HTMLResponse)
def customer_detail(
    request: Request,
    customer_id: str,
    list: str | None = Query(default=None),
    db: Session = Depends(get_db)
):
    
    # Capture all query parameters as a dict
    query_params = dict(request.query_params)

    customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id)
        .first()
    )

    callers = (
        db.query(Caller)
        .all()
    )

    customer.caller_id = int(customer.caller_id) if customer.caller_id is not None else None

    print(customer.to_dict())

# Example: log all query params
    print(f"Query params received: {query_params}")

    if list == "short":
        # Render short template
        return templates.TemplateResponse(
            "customers/info.html",
            {
                "request": request, 
                "customer": customer, 
                "customer_id": customer_id, 
                "categories": categories,
                "organisations": organisations, 
                "callers": callers,
            }
        )
    else:
        # Render full template
        return templates.TemplateResponse(
            "customers/edit.html",
            {
                "request": request, 
                "customer": customer, 
                "categories": categories, 
                "organisations": organisations, 
                "callers": callers,
            }
        )  
         

# DELETE customer
@router.post("/delete/{customer_id}", name="delete_customer")
def delete_customer(customer_id: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    db.delete(customer)
    db.commit()
    return {"detail": f"Customer {customer_id} deleted successfully"}

