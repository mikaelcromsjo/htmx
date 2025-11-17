# products.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi import APIRouter, Depends, Form, Request, HTTPException, Query

import data.constants as constants
from datetime import datetime, timezone

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
from models.models import Product, ProductUpdate, ProductCustomer, Customer
from models.models import Update
from core.functions.helpers import populate, local_to_utc

router = APIRouter(prefix="/products", tags=["products"])

# -----------------------------
# List Products (HTMX fragment)
# -----------------------------
@router.get("/", response_class=HTMLResponse, name="products_list")
def products_list(
    request: Request,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):

    # list all that has not ended now() - 30 days
    product_date_filter_start = datetime.now(timezone.utc) - timedelta(days=constants.SHOW_PRODUCTS_X_DAYS)
    query = select(Product)

    if product_date_filter_start:
        query = query.where(Product.end_date >= product_date_filter_start)

    products = db.execute(query).scalars().all()

    return templates.TemplateResponse(
        "products/list.html", {
            "request": request, "products": products, "is_admin": user.admin, "products_map": constants.products_map
}
    )

# -----------------------------
# Product Detail Modal (HTMX fragment)
# -----------------------------
@router.get("/new", name="new_product", response_class=HTMLResponse)
def new_product(
    request: Request,
    db: Session = Depends(get_db),
):
    product = Product.empty()

    return templates.TemplateResponse(
        "products/edit.html", {
            "request": request, 
            "product": product, 
            "editable": True}
    )               

# -----------------------------
# Product Detail Modal (HTMX fragment)
# -----------------------------
@router.get("/product/{product_id}", response_class=HTMLResponse)
def product_detail(
    request: Request,
    product_id: int,
    user = Depends(get_current_user),
    list: str | None = Query(default=None),
    status_filter: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    
    product = db.get(Product, product_id)
    if not product:
        product = Product().empty()

    if list == "short":

    # Query product customers
        query = db.query(ProductCustomer).join(Customer).filter(ProductCustomer.product_id == product_id)
        product_customers = query.all()

        totals = {"s1":0, "s2":0, "s3":0, "s4":0, "s5":0, "s6":0, "s7":0, "all":0}
        for ec in product_customers:
            totals["all"] += 1
            if ec.status == 2:
                totals["s2"] += 1
            elif ec.status == 1:
                totals["s1"] += 1
            elif ec.status == 3:
                totals["s3"] += 1
            elif ec.status == 4:
                totals["s4"] += 1
            elif ec.status == 5:
                totals["s5"] += 1
            elif ec.status == 6:
                totals["s6"] += 1
            elif ec.status == 7:
                totals["s7"] += 1
        
        if status_filter is not None:
            query = query.filter(ProductCustomer.status == status_filter)        
        else:
            status_filter = 0
        product_customers = query.all()

        # Render short template
        return templates.TemplateResponse(
            "products/info.html",
            {
                "request": request, 
                "product": product, 
                "product_customers": product_customers,
                "totals": totals,
                "status_filter": status_filter,
                "user": user,
                "products_map": constants.products_map,
                "products_json": constants.products,
                "filters_map": constants.filters_map
            }
        )
    else:
        # Render full template
        return templates.TemplateResponse(
            "products/edit.html", {"request": request, 
                                   "product": product, 
                                   "editable": True,
                                    "products": constants.products,
                                    }
        )
     

from sqlalchemy.inspection import inspect

def to_dict(obj):
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


# -----------------------------
# Update Existing Product
# -----------------------------

@router.post("/product/upsert", name="upsert_product", response_class=HTMLResponse)
async def upsert_product(
    request: Request,
    update_data: Update,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    
    if not user.admin:
        raise HTTPException(status_code=401, detail="Error. Only Admin can edit products")

    # make input dates utc
    update_data.start_date = local_to_utc(update_data.start_date)
    update_data.end_date = local_to_utc(update_data.end_date)

    # Determine if this is an update or create
    product_id = update_data.model_dump().get("id")
    if product_id:
        try:
            product_id_int = int(product_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid product ID")
        product = db.query(Product).filter(Product.id == product_id_int).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
    else:
        product = Product().empty()


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
    product = populate(data_dict, product, ProductUpdate)
    db.add(product)

    db.commit()
    db.refresh(product)

    # Render updated list (HTMX swap)
    products = db.query(Product).all()
    response = templates.TemplateResponse(
        "products/list.html",
        {
            "request": request, 
            "products": products,
            "products_map": constants.products_map,
         },
    )
    # Set the popup message in a custom header
    response.headers["HX-Popup-Message"] = "Saved"
    response.headers["HX-Trigger"] = "callsProductsReload"
    return response

# DELETE product
@router.post("/delete/{product_id}", name="delete_product")
def delete_product(product_id: str, db: Session = Depends(get_db), user = Depends(get_current_user)):

    if not user.admin:
        return {"detail": f"Error. Only Admin can delete products"}


    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return {"detail": f"Product {product.name} deleted successfully"}

@router.post("/set_filter", name="set_filter", response_class=HTMLResponse)
async def set_filter(
    request: Request,
    db: Session = Depends(get_db),
):
    data = await request.json()

    start_str = data.get("product_date_filter-start")
    end_str = data.get("product_date_filter-end")

    # Convert to UTC-aware datetimes if provided
    product_date_filter_start = local_to_utc(start_str) if start_str else None
    product_date_filter_end = (local_to_utc(end_str) + timedelta(days=1)) if end_str else None
    query = select(Product)

    if product_date_filter_start and product_date_filter_end:
        query = query.where(
            Product.start_date >= product_date_filter_start,
            Product.start_date < product_date_filter_end
        )
    elif product_date_filter_start:
        query = query.where(Product.start_date >= product_date_filter_start)
    elif product_date_filter_end:
        query = query.where(Product.start_date < product_date_filter_end)
    # else: no filter, return all products

    products = db.execute(query).scalars().all()

    response = templates.TemplateResponse(
        "products/list.html",
        {"request": request, "products": products, "products_map": constants.products_map}
    )
    response.headers["HX-Popup-Message"] = "Updated"
    return response
