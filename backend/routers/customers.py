from fastapi import APIRouter, Depends, Form, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.orm import Session

from pydantic import BaseModel, Field

from typing import List, Optional, Dict, Any
from typing import Any, Union, Optional, get_origin, get_args

from core.models.base import Base
from core.database import get_db
from core.functions.helpers import render
from templates import templates
from data.constants import categories, organisations, personalities
from data.constants import categories_map, organisations_map, personalities_map
from models.models import Customer, CustomerUpdate, Caller
from core.functions.helpers import populate, build_filters

from models.models import Update
from core.auth import get_current_user
from core.models.models import BaseMixin, Update, User

from functions.customers import get_user_customers



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
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    print("Admin:", user.admin)
    customers = get_user_customers(db, request, user)
    return templates.TemplateResponse(
        "customers/list.html",
        {"request": request, 
         "customers": customers,
         "is_admin": user.admin,
        }
    )




@router.post("/customer/upsert", name="upsert_customer", response_class=HTMLResponse)
async def upsert_customer(
    request: Request,
    update_data: Update,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):

    # Determine if this is an update or create
    id = update_data.model_dump().get("id")
    if id:
        try:
            id_int = int(id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Customer ID")
        data_record = db.query(Customer).filter(Customer.id == id_int).first()
        if not data_record:
            raise HTTPException(status_code=404, detail="Customer not found")
    else:
        data_record = Customer()

    data_dict = update_data.model_dump()

    # Ensure 'extra' exists and is a dict
    if 'extra' not in data_dict or not isinstance(data_dict['extra'], dict):
        data_dict['extra'] = {}

    # Move any keys that start with "extra." into the extra dict
    for key, value in list(data_dict.items()):
        if key.startswith("extra."):
            field_name = key.split(".", 1)[1]  # remove "extra."
            data_dict['extra'][field_name] = value
            del data_dict[key]  # optionally clean up the flat key
            
    # --- Temporarily remove relationships before populate ---
    caller_id = (data_dict.pop("caller_id", None))  # remove 'caller' from dict
    if caller_id:
        caller_id = int(caller_id)

    # Populate DB model dynamically (everything except relationships)
    data_record = populate(data_dict, data_record, CustomerUpdate)
    print ("caller_id", caller_id)
    # --- Handle relationships AFTER populate ---
    if isinstance(caller_id, int):
        caller_instance = db.get(Caller, int(caller_id))
        print ("instance", caller_instance)
        if not caller_instance:
            raise HTTPException(status_code=404, detail="Caller not found")
        data_record.caller = caller_instance  # assign the actual SQLAlchemy object


    # Normalize CSV: remove extra spaces and surrounding quotes
    if data_record.tags:
        tags_clean = ",".join(v.strip().strip("'\"") for v in data_record.tags.split(",") if v.strip())
        data_record.tags = tags_clean

    db.add(data_record)
    db.commit()
    print(repr(data_record.tags))  # should output: 'a,c,d' without extra quotes or spaces    
    db.refresh(data_record)

    # Render updated list (HTMX swap)
    customers = get_user_customers(db, request, user)

    response =  templates.TemplateResponse(
        "customers/list.html",
        {
            "request": request, 
            "customers": customers,
            "detail": "Updated"},
    )
    # Set the popup message in a custom header
    response.headers["HX-Popup-Message"] = "Saved"
    response.headers["HX-Trigger"] = "dashboardReload"
    return response

@router.get("/customer/{customer_id}", response_class=HTMLResponse)
def customer_detail(
    request: Request,
    customer_id: str,
    user = Depends(get_current_user),
    list: str | None = Query(default=None),
    db: Session = Depends(get_db)
):
    

    if (customer_id and int(customer_id) > 0):
        customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        customer = (
            db.query(Customer)
            .filter(Customer.id == customer_id)
            .first()
        )
    else:
        customer = Customer.empty()
        customer.caller_id = user.caller_id

    # all callers for all users
    if False:
        callers = (
            db.query(Caller)
            .filter(Caller.id == user.caller.id)
            .all()
        )
    else:
        callers = db.query(Caller).all()

    customer.caller_id = int(customer.caller_id) if customer.caller_id is not None else None

    print(customer.to_dict())

    if list == "short":
        # Render short template
        return templates.TemplateResponse(
            "customers/info.html",
            {
                "request": request, 
                "customer": customer, 
                "customer_id": customer_id, 
                "categories_map": categories_map,
                "organisations_map": organisations_map, 
                "personalities_map": personalities_map, 
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
                "personalities": personalities, 
                "callers": callers,
            }
        )  
         

# DELETE customer
@router.post("/delete/{customer_id}", name="delete_customer")
def delete_customer(customer_id: str, db: Session = Depends(get_db), user = Depends(get_current_user)):

    if not user.admin:
        return {"detail": f"Error. Only Admin can delete customers"}

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    db.delete(customer)
    db.commit()
    return {"detail": f"Customer {customer_id} deleted successfully"}



@router.get("/filter", response_class=HTMLResponse)
def customer_filter(
    request: Request,
    db: Session = Depends(get_db)
):
        
    callers = (
        db.query(Caller)
        .all()
    )

    filter_dict = {}

    return templates.TemplateResponse(
        "customers/filter.html",
        {
            "request": request, 
            "filters": filter_dict, 
            "categories": categories, 
            "organisations": organisations, 
            "personalities": personalities, 
            "callers": callers,
        }
    )

from sqlalchemy import or_, and_

@router.post("/set_filter", name="set_filter", response_class=HTMLResponse)
async def set_filter(
    request: Request,
    update_data: Update,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    data_dict = update_data.model_dump()
    print (data_dict)


    # save filters definition (not SQLAlchemy objects) in session
    request.session["customer_filters"] = data_dict 

    customers = get_user_customers(db, request, user)

    return templates.TemplateResponse(
        "customers/list.html",
        {"request": request, "customers": customers}
    )
