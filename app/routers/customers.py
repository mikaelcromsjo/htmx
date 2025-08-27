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
from app.models.models import Customer
from app.functions.helpers import populate

class Update(BaseModel):
    class Config:
        extra = "allow"

class CustomerUpdate(BaseModel):
    first_name: str
    last_name: str
    user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    comment: Optional[str] = None
    sub_caller: Optional[str] = None
    organisations: Optional[List[str]] = []      # Multi-select → list
    personality_type: Optional[int] = None       # Dropdown → int
    contributes: Optional[int] = None            # Dropdown → int
    caller: Optional[int] = None                 # Dropdown → int
    controlled: Optional[bool] = False           # Checkbox → bool
    likes_parties: Optional[bool] = False        # Checkbox → bool
    likes_politics: Optional[bool] = False
    likes_lectures: Optional[bool] = False
    likes_activism: Optional[bool] = False
    categories: Optional[List[str]] = []         # Multi-select → list
    tags: Optional[str] = ""                      # Comma-separated → list in populate()
    extra: Optional[str] = "{}"                   # JSON string → dict in populate()
    code_name: Optional[bool] = False            # Checkbox → bool    

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
        {"request": request, "customers": customers, "filter": filter},
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


    return templates.TemplateResponse(
        "customers/edit.html",
        {
            "request": request, 
            "customer": customer, 
            "mode": "edit",
            "categories": categories,
            "organisations": organisations, 
        }
    )

@router.post("/edit", name="edit", response_class=HTMLResponse)
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

    print(update_data.model_dump())

    # Populate DB model dynamically
    customer = populate(update_data.model_dump(), customer, CustomerUpdate)

    db.add(customer)
    db.commit()
    db.refresh(customer)

    # Render updated list (HTMX swap)
    customers = db.query(Customer).all()
    return templates.TemplateResponse(
        "customers/list.html",
        {"request": request, "customers": customers},
    )


@router.get("/get/{customer_id}", response_class=HTMLResponse)
def customer_detail(
    request: Request,
    customer_id: str,
    list: str | None = Query(default=None, description="Optional list parameter, e.g., 'short'"),
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
            }
        )
    else:
        # Render full template
        return templates.TemplateResponse(
            "customers/edit.html",
            {
                "request": request, 
                "customer": customer, 
                "mode": "edit",
                "categories": categories,
                "organisations": organisations, 
            }
        )  
         

# DELETE customer
@router.post("/delete/{customer_id}", name="customer_delete")
def customer_delete(customer_id: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    db.delete(customer)
    db.commit()
    return {"detail": f"Customer {customer_id} deleted successfully"}

