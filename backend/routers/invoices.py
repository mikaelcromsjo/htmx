# invoices.py
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
from models.models import Invoice, InvoiceUpdate
from models.models import Update, Customer
from core.functions.helpers import populate
from core.auth import get_current_user
from datetime import date


router = APIRouter(prefix="/invoices", tags=["invoices"])

# -----------------------------
# List invoices (HTMX fragment)
# -----------------------------
@router.get("/", response_class=HTMLResponse, name="invoices_list")
def invoices_list(
    request: Request,
    filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = select(Invoice)
    if filter:
        query = query.where(Invoice.name.contains(filter))
    invoices = db.execute(query).scalars().all()
    return templates.TemplateResponse(
        "invoices/list.html", {"request": request, "invoices": invoices}
    )



# -----------------------------
# Invoice Detail Modal (HTMX fragment)
# -----------------------------
@router.get("/new", name="new_invoice", response_class=HTMLResponse)
def new_invoice(
    request: Request,
    db: Session = Depends(get_db),
):
    invoice = Invoice.empty()

    customers = db.query(Customer).all()

    return templates.TemplateResponse(
        "invoices/edit.html", {"request": request, "invoice": invoice, "editable": True, "customers": customers}
    )               

# -----------------------------
# Invoice Detail Modal (HTMX fragment)
# -----------------------------
@router.get("invoice/{invoice_id}", response_class=HTMLResponse)
def invoice_detail(
    request: Request,
    invoice_id: int,
    list: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    
    # Capture all query parameters as a dict
    query_params = dict(request.query_params)

    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="invoice not found")


    # Get current user
    current_user = get_current_user(request, db)
    customers = db.query(Customer).filter(Customer.caller_id == current_user.caller_id).all()


    # Invoice company data for testing
    invoice_data = {
        "name": "My Company AB",
        "address_line1": "Company Street 1",
        "address_line2": "Suite 100",
        "postal_code": "54321",
        "postal_address": "Berga",
        "country": "Sweden",
        "vat_number": "SE9876543210",
        "bank_name": "banknamn",
        "iban": "345678",
        "bic": "43345678",
        "bankgiro": "bg-43345678",
        "plusgiro": "pg-43345678",
        "note": "This is a test invoice for demonstration purposes."
    }


    if list == "short":
        # Render short template
        return templates.TemplateResponse(
            "invoices/info.html",
            {
                "request": request, 
                "invoice": invoice, 
                "invoice_data": invoice_data, 
                "customers": customers
            }
        )
    else:
        # Render full template
        return templates.TemplateResponse(
            "invoices/edit.html", {"request": request, "invoice": invoice, "editable": True, "customers": customers}
        )
     


def normalize_extra_rows(extra: dict) -> dict:

    rows = {}
    keys_to_remove = []

    for key, value in extra.items():
        if key.startswith("row."):
            parts = key.split(".")  # ['row', '1', 'description']
            if len(parts) == 3:
                _, rownum, field = parts
                rows.setdefault(rownum, {})[field] = value
                keys_to_remove.append(key)

    # Remove flat row keys
    for key in keys_to_remove:
        extra.pop(key)

    # Add normalized rows
    extra["row"] = rows

    return extra

# -----------------------------
# Update Existing invoice
# -----------------------------

@router.post("/invoice", name="upsert_invoice", response_class=HTMLResponse)
async def upsert_invoice(
    request: Request,
    update_data: Update,
    db: Session = Depends(get_db),
):

    # Determine if this is an update or create
    invoice_id = update_data.model_dump().get("id")
    if invoice_id:
        try:
            invoice_id_int = int(invoice_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid invoice ID")
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id_int).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="invoice not found")
    else:
        invoice = Invoice()


    data_dict = update_data.model_dump(exclude_unset=True)

#    date_str = data_dict.get("date") 
#    if date_str:
#        data_dict["date"] = datetime.strptime(date_str, "%Y-%m-%d")
#    else:
#        data_dict["date"] = None

    # Ensure 'extra' exists and is a dict
    if 'extra' not in data_dict or not isinstance(data_dict['extra'], dict):
        data_dict['extra'] = {}

    # Move any keys that start with "extra." into the extra dict
    for key, value in list(data_dict.items()):
        if key.startswith("extra."):
            field_name = key.split(".", 1)[1]  # remove "extra."
            data_dict['extra'][field_name] = value
            print("value", field_name, value)
            del data_dict[key]  # optionally clean up the flat key

    data_dict['extra'] = normalize_extra_rows(data_dict['extra'])

    # Populate DB model dynamically
    invoice = populate(data_dict, invoice, InvoiceUpdate)

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    # Render updated list (HTMX swap)
    invoices = db.query(Invoice).all()
    response = templates.TemplateResponse(
        "invoices/list.html",
        {"request": request, "invoices": invoices},
    )
    # Set the popup message in a custom header
    response.headers["HX-Popup-Message"] = "Saved"
    return response



# DELETE invoice
@router.post("/delete/{invoice_id}", name="delete_invoice")
def delete_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    db.delete(invoice)
    db.commit()
    return {"detail": f"Invoice {invoice.name} deleted successfully"}

