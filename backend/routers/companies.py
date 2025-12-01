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
import data.constants as constants
from models.models import Company, CompanyUpdate, Caller
from core.functions.helpers import populate, build_filters

from models.models import Update


# -------------------------------------------------
# Router & Templates Setup
# -------------------------------------------------
router = APIRouter(prefix="/companies", tags=["companies"])

# -------------------------------------------------
# List Companies
# Returns an HTMX fragment with list.html
# -------------------------------------------------
@router.get("/", response_class=HTMLResponse, name="companies_list")
def companies_list(
    request: Request,
    db: Session = Depends(get_db)
):

    query = db.query(Company)
    companies = query.all()

    return render(
        "companies/list.html",
        {"request": request, 
         "companies": companies,
         },
    )


# -------------------------------------------------
# Company Detail
# Returns companies/edit.html
# -------------------------------------------------


@router.get("/new", response_class=HTMLResponse) 
def company_new(
    request: Request,
    db: Session = Depends(get_db)
):

    company = Company.empty()

    query = db.query(Caller)
    callers = query.all()

    return templates.TemplateResponse(
        "companies/edit.html",
        {
            "request": request, 
            "company": company, 
            "mode": "edit",
            "categories": constants.categories,
            "callers": callers, 
        }
    )



@router.post("/company/upsert", name="upsert_company", response_class=HTMLResponse)
async def upsert_company(
    request: Request,
    update_data: Update,
    db: Session = Depends(get_db),
):

    # Determine if this is an update or create
    id = update_data.model_dump().get("id")
    if id:
        try:
            id_int = int(id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Company ID")
        data_record = db.query(Company).filter(Company.id == id_int).first()
        if not data_record:
            raise HTTPException(status_code=404, detail="Company not found")
    else:
        data_record = Company()

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
    data_record = populate(data_dict, data_record, CompanyUpdate)
    print ("caller_id", caller_id)
    # --- Handle relationships AFTER populate ---
    if isinstance(caller_id, int):
        caller_instance = db.get(Caller, int(caller_id))
        print ("instance", caller_instance)
        if not caller_instance:
            raise HTTPException(status_code=404, detail="Caller not found")
        data_record.caller = caller_instance  # assign the actual SQLAlchemy object


    db.add(data_record)
    db.commit()
    db.refresh(data_record)

    # Render updated list (HTMX swap)
    companies = db.query(Company).all()
    response =  templates.TemplateResponse(
        "companies/list.html",
        {
            "request": request, 
            "companies": companies,
            "detail": "Updated"},
    )
    # Set the popup message in a custom header
    response.headers["HX-Popup-Message"] = "Saved"
    return response




@router.get("/company/{company_id}", response_class=HTMLResponse)
def company_detail(
    request: Request,
    company_id: str,
    list: str | None = Query(default=None),
    db: Session = Depends(get_db)
):
    
    # Capture all query parameters as a dict
    query_params = dict(request.query_params)

    if (company_id and int(company_id) > 0):
        company = db.query(Company).filter(Company.id == int(company_id)).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        company = (
            db.query(Company)
            .filter(Company.id == company_id)
            .first()
        )
    else:
        company = Company.empty()

    callers = (
        db.query(Caller)
        .all()
    )

    company.caller_id = int(company.caller_id) if company.caller_id is not None else None

    print(company.to_dict())

# Example: log all query params
    print(f"Query params received: {query_params}")

    if list == "short":
        # Render short template
        return templates.TemplateResponse(
            "companies/info.html",
            {
                "request": request, 
                "company": company, 
                "company_id": company_id, 
                "categories_map": constants.categories_map,
                "organisations_map": constants.organisations_map, 
                "filters_map": constants.filters_map, 
                "personalities_map": constants.personalities_map, 
                "callers": callers,
            }
        )
    else:
        # Render full template
        return templates.TemplateResponse(
            "companies/edit.html",
            {
                "request": request, 
                "company": company, 
            }
        )  
         

# DELETE company
@router.post("/delete/{company_id}", name="delete_company")
def delete_company(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    db.delete(company)
    db.commit()
    return {"detail": f"Company {company_id} deleted successfully"}



@router.get("/filter", response_class=HTMLResponse)
def company_filter(
    request: Request,
    db: Session = Depends(get_db)
):
        
    callers = (
        db.query(Caller)
        .all()
    )

    filter_dict = {}
#    filters = build_filters(data_dict, Company)

    return templates.TemplateResponse(
        "companies/filter.html",
        {
            "request": request, 
            "filters": filter_dict, 
            "categories": constants.categories, 
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
    filters = build_filters(data_dict, Company)

    # save filters definition (not SQLAlchemy objects) in session
    request.session["company_filters"] = data_dict  

    # later you can re-run build_filters(request.session["company_filters"], Company)

    query = db.query(Company)
    filters = build_filters(data_dict, Company)
    if filters:
        query = query.filter(*filters)
    companies = query.all()

    return templates.TemplateResponse(
        "companies/list.html",
        {"request": request, "companies": companies}
    )
