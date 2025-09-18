

from sqlalchemy.orm import Session, declarative_base
from typing import List, Optional
from app.models.models import Customer
from sqlalchemy.orm import Session, joinedload
from app.core.models.base import Base
from fastapi import Request
from pydantic import BaseModel, Field

from typing import List, Optional

class SelectedIDs(BaseModel):
    ids: List[int] = Field(..., alias="selected_ids")

def get_selected_ids(request: Request, selected_ids: Optional[SelectedIDs]) -> List[int]:
    """
    Helper to manage selected IDs in session.
    """
    if selected_ids is not None:
        # Save to session if POSTed
        request.session["selected_ids"] = selected_ids.ids
        return selected_ids.ids
    # Otherwise, pull from session
    return request.session.get("selected_ids", [])

def get_customers(db: Session, ids: List[int]):
    """
    Helper to query customers from DB based on IDs.
    """
    query = db.query(Customer)
    if ids:
        return query.filter(Customer.id.in_(ids)).all()
    return query.all()