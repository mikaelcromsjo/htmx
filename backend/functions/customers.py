

from sqlalchemy.orm import Session, declarative_base
from typing import List, Optional
from models.models import Customer, Caller
from sqlalchemy.orm import Session, joinedload
from core.models.base import Base
from fastapi import Request
from pydantic import BaseModel, Field
from core.functions.helpers import build_filters
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

def get_customers(db: Session, user, ids: List[int]):
    """
    Helper to query customers from DB based on IDs.
    """
    query = db.query(Customer)
    if user.admin != 1:
        query = query.filter(Customer.caller_id == user.caller.id)
    if ids:
        return query.filter(Customer.id.in_(ids)).all()
    return query.all()


def get_user_customers(db, request, user):
    query = db.query(Customer)

    if user.admin != 1:
        query = query.filter(Customer.caller_id == user.caller_id)


    session = db
    try:
        callers = session.query(Caller).order_by(Caller.id).limit(10).all()
        print("Caller IDs and names:")
        for c in callers:
            print(f"ID: {c.id}, Name: {c.name}")
    finally:
        session.close()

    try:
        count = session.query(Customer).filter(Customer.caller_id == 7).count()
        print(f"Customers for caller_id 7: {count}")
    finally:
        session.close()

    try:
        customers = session.query(Customer).order_by(Customer.id).limit(20).all()
        print("Customer IDs, names, and caller_id:")
        for c in customers:
            print(f"ID: {c.id}, Name: {c.first_name} {c.last_name}, Caller ID: {c.caller_id}, User ID: {c.user_id}")
    finally:
        session.close()

    filter_dict = request.session.get("customer_filters", {})
    filters = build_filters(filter_dict, Customer)

    sql_filters, exact_filters = get_exact_vals(filters)

    if sql_filters:
        query = query.filter(*sql_filters)

    rows = query.all()

    # Apply Python-side "exact" matching
    if exact_filters:
        rows = exact_vals(rows, exact_filters)

    return rows


def get_exact_vals(filters):
    """Separate SQLAlchemy filters from Python-side exact match filters."""
    exact_filters = [f for f in filters if isinstance(f, dict) and "exact_vals" in f]
    sql_filters = [f for f in filters if not (isinstance(f, dict) and "exact_vals" in f)]
    return sql_filters, exact_filters

def exact_vals(rows, exact_filters):
    results = []
    for row in rows:
        include = True
        for f in exact_filters:
            colname = f["column"]
            expected_vals = set(f["exact_vals"])
            raw_val = getattr(row, colname, None)

            if raw_val is None:
                include = False
                break

            # Normalize actual values (works for CSV or JSON)
            if isinstance(raw_val, list):
                actual_vals = set(str(v) for v in raw_val)
            else:
                actual_vals = set(v.strip() for v in str(raw_val).split(",") if v.strip())

            if actual_vals != expected_vals:
                include = False
                break

        if include:
            results.append(row)
    return results