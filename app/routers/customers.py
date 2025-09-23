from fastapi import APIRouter, Depends, Form, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.orm import Session

from pydantic import BaseModel, Field

from typing import List, Optional, Dict, Any
from typing import Any, Union, Optional, get_origin, get_args

from app.core.models.base import Base
from app.core.database import get_db
from app.core.functions.helpers import render
from app.templates import templates
from app.data.constants import categories, organisations, personalities
from app.data.constants import categories_map, organisations_map, personalities_map
from app.models.models import Customer, CustomerUpdate, Caller
from app.core.functions.helpers import populate

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
            "personalities": personalities, 
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
    print(data_dict)

    # --- Temporarily remove relationships before populate ---
    caller_id = int(data_dict.pop("caller_id", None))  # remove 'caller' from dict

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
def delete_customer(customer_id: str, db: Session = Depends(get_db)):
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
#    filters = build_filters(data_dict, Customer)

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
):
    data_dict = update_data.model_dump()
    print (data_dict)

    # build SQLAlchemy filters
    filters = build_filters(data_dict, Customer)

    # save filters definition (not SQLAlchemy objects) in session
    request.session["customer_filters"] = data_dict  

    # later you can re-run build_filters(request.session["customer_filters"], Customer)

    query = db.query(Customer)
    filters = build_filters(data_dict, Customer)
    if filters:
        query = query.filter(*filters)
    customers = query.all()

    return templates.TemplateResponse(
        "customers/list.html",
        {"request": request, "customers": customers}
    )

from sqlalchemy import and_, or_, Date, DateTime, Boolean, String, Integer
from sqlalchemy.inspection import inspect
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON as SQLAlchemyJSON

def build_filters(data: dict, model):
    """
    Build SQLAlchemy filters from form data.
    Handles:
        - Scalar integers (caller, personality_type, contributes)
        - Booleans
        - Text fields
        - Multi-select / JSON / text array fields
        - Dates with start/end
        - Filter types: exact, has, has-all, has-not, like, true, false
    Prints exact SQLAlchemy filters.
    """
    filters = []
    mapper = inspect(model)
    column_types = {col.name: col.type for col in mapper.columns}


    for field, value in data.items():
        # Skip None or empty string
        if value in (None, ""):
            continue

        print("data", field, value)


        # BOOLEAN *_type
        if field.endswith("_type") and field[:-5] in column_types:
            print("bool")

            base_field = field[:-5]
            col = getattr(model, base_field)
            col_type = column_types.get(base_field)
            if isinstance(col_type, Boolean):
                val_str = str(value).lower()
                if val_str == "true":
                    f = col == True
                elif val_str == "false":
                    f = col == False
                else:
                    continue
                print(f"Adding filter: {f}")
                filters.append(f)
                continue

        # DATE ranges
        base_field = field
        is_start = False
        is_end = False
        if field.endswith("-start"):
            base_field = field[:-6]
            is_start = True
        elif field.endswith("-end"):
            base_field = field[:-4]
            is_end = True

        col = getattr(model, base_field, None)
        if not col:
            continue

        col_type = column_types.get(base_field)

       # 👇 Debug line here
        print(f"DEBUG field={base_field}, type={type(col_type)}, col_type={col_type}")

        filter_type = data.get(f"{field}_type", "like")

        # DATE
        if isinstance(col_type, (Date, DateTime)):
            print("date")
            if is_start:
                f = col >= value
            elif is_end:
                f = col <= value
            else:
                f = col == value
            print(f"Adding filter: {f}")
            filters.append(f)
            continue

        # INTEGER SCALAR (caller, personality_type, contributes)
        if isinstance(col_type, Integer):
            print("integer")
            vals = value if isinstance(value, list) else [value]
            # filter out empty strings / None
            vals = [v for v in vals if v not in (None, "", [])]
            if not vals:
                continue
            try:
                vals = [int(v) for v in vals]
            except ValueError:
                continue

            if filter_type in ("exact", "has"):
                if len(vals) == 1 and filter_type == "exact":
                    f = col == vals[0]
                else:
                    f = col.in_(vals)   # <- for 'has', use in_()
            elif filter_type == "has-not":
                f = ~col.in_(vals)

            print(f"Adding filter: {f}")
            filters.append(f)
            continue

        if isinstance(col_type, String):
            print ("string")
            vals = value if isinstance(value, list) else [value]
            # filter out empty / None
            vals = [str(v) for v in vals if v not in (None, "")]
            if not vals:
                continue

            if filter_type == "has":
                f = or_(*[col.contains(v) for v in vals])
            elif filter_type == "has-all":
                f = and_(*[col.contains(v) for v in vals])
            elif filter_type == "has-not":
                f = and_(*[~col.contains(v) for v in vals])
            elif filter_type == "exact":
                f = or_(*[col == v for v in vals])
            elif filter_type == "like":
                f = col.ilike(f"%{vals[0]}%")  # only first for single value

            if f is not None:
                print(f"Adding filter: field={field}, type={filter_type}, value={vals}, filter={f}")
                filters.append(f)

        if isinstance(col_type, ARRAY):
            print("array")
            vals = value if isinstance(value, list) else [value]
            vals = [v for v in vals if v not in (None, "", [])]
            if not vals:
                continue

            if filter_type == "has":
                # Matches if *any* element is present
                f = or_(*[col.any(v) for v in vals])
            elif filter_type == "has-all":
                # All must be present
                f = and_(*[col.any(v) for v in vals])
            elif filter_type == "has-not":
                f = and_(*[~col.any(v) for v in vals])
            elif filter_type == "exact":
                # Whole array equality
                f = col == vals
            else:
                continue

            print(f"Adding filter: field={field}, type={filter_type}, value={vals}, filter={f}")
            filters.append(f)
            continue

        # JSON / JSONB fields
        if isinstance(col_type, (SQLAlchemyJSON, JSONB)):
            print("json")
            vals = value if isinstance(value, list) else [value]
            vals = [v for v in vals if v not in (None, "", [])]
            if not vals:
                continue

            if filter_type == "has":
                # any value present
                f = or_(*[col.contains([v]) for v in vals])
            elif filter_type == "has-all":
                # must contain all
                f = col.contains(vals)
            elif filter_type == "has-not":
                f = and_(*[~col.contains([v]) for v in vals])
            elif filter_type == "exact":
                f = col == vals
            else:
                continue

            print(f"Adding filter: field={field}, type={filter_type}, value={vals}, filter={f}")
            filters.append(f)
            continue

                
    return filters
