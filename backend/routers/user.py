from fastapi import APIRouter, Depends, Form, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from pydantic import BaseModel, Field

from typing import List, Optional, Dict, Any
from typing import Any, Union, Optional, get_origin, get_args

from core.models.base import Base
from core.database import get_db
from core.functions.helpers import render
from templates import templates
import data.constants as constants
from core.models.models import User, UserUpdate
from core.functions.helpers import populate, build_filters

from models.models import Update
from core.auth import get_current_user


# -------------------------------------------------
# Router & Templates Setup
# -------------------------------------------------
router = APIRouter(prefix="/user", tags=["user"])

# -------------------------------------------------
# List Customers
# Returns an HTMX fragment with list.html
# -------------------------------------------------
@router.get("/", response_class=HTMLResponse, name="user")
def user(
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)

    if not user:
        user = User.empty()

    return render(
        "user/info.html",
        {"request": request, 
         "user": user},
    )


@router.post("/user/upsert", name="upsert_user", response_class=HTMLResponse)
async def upsert_user(
    request: Request,
    update_data: Update,
    db: Session = Depends(get_db),
):

    data_record = get_current_user(request, db)

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

    # Populate DB model dynamically (everything except relationships)
    data_record = populate(data_dict, data_record, UserUpdate)

    try:
        db.add(data_record)
        db.commit()
        db.refresh(data_record)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    response = templates.TemplateResponse(
        "user/info.html",
        {
            "request": request,
            "user": data_record
        }
    )
    # Set the popup message in a custom header
    response.headers["HX-Popup-Message"] = "Saved"
    return response

