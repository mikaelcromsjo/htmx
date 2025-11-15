# app/routers/calls.py

from fastapi import APIRouter, Depends, Request, Form, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

import data.constants as constants

from core.database import get_db
from templates import templates


from models.models import Customer, Call, Product, ProductCustomer, Caller, Alarm
from core.functions.helpers import render
from functions.customers import get_selected_ids, get_customers, SelectedIDs

import data.constants as constants
from core.auth import get_current_user



router = APIRouter(prefix="/calls", tags=["calls"])



# ---------------------------
# Dashboard View
# ---------------------------

@router.api_route("/dashboard", methods=["GET", "POST"], response_class=HTMLResponse, name="calls_dashboard")
def call_center_dashboard(
    request: Request,
    selected_ids: Optional[SelectedIDs] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Single route to render the call center dashboard for both GET and POST.
    """
    ids = get_selected_ids(request, selected_ids)

    customers = get_customers(db, user, ids)
#    query = db.query(Call)
#    calls = query.all()
    query = db.query(Product)
    products = query.all()

    return render(
        "calls/dashboard.html",
        {"request": request, "customers": customers, "products": products, "products_json": constants.products },
    )


@router.get("/customers", response_class=HTMLResponse, name="calls_customers_list")
def call_customers_list(
    request: Request,
    selected_ids: Optional[SelectedIDs] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    
    ids = get_selected_ids(request, selected_ids)
    customers = get_customers(db, user, ids)

    return render(
        "calls/customers_list.html",
        {"request": request, "customers": customers}, 
    )



# -----------------------------
# Customer Details and call list (HTMX fragment)
# -----------------------------

from sqlalchemy import desc
from state import user_data, active_connections
from core.models.models import BaseMixin, Update, User

@router.get("/customer_data", name="customer_data", response_class=HTMLResponse, response_model=None)
async def customer_data(
    request: Request,
    customer_id: int = Query(default=0),
    db = Depends(get_db),
    user = Depends(get_current_user)
):
    
    user_id = user.id

    customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")


    user_data.setdefault(user_id, {})["name"] = customer.first_name + " " + customer.last_name
    user_data.setdefault(user_id, {})["number"] = customer.phone
    # Broadcast to all connected receivers

    to_remove = []

    print("send", user_id)

    for ws in active_connections.get(str(user_id), []):
        print("send2")

        try:
            await ws.send_json(user_data[user_id])
        except RuntimeError:
            to_remove.append(ws)

    for ws in to_remove:
        active_connections[user_id].remove(ws)

    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id)
        .first()
    )
    
    callers = (
        db.query(Caller)
        .all()
    )    

    # Limit to 50 calls
    calls = db.query(Call).filter(Call.customer_id == int(customer_id)).order_by(desc(Call.id)).limit(50).all()

    return templates.TemplateResponse(
        "calls/customer_calls.html",
        {
            "request": request, 
            "customer": customer,
            "categories_map": constants.categories_map,
            "organisations_map": constants.organisations_map, 
            "filters_map": constants.filters_map, 
            "personalities_map": constants.personalities_map, 
            "callers": callers,
            "customer": customer,
            "calls": calls
        }
    )


# -----------------------------
# List Calls (HTMX fragment)
# -----------------------------


@router.get("/customer/{customer_id}", response_class=HTMLResponse)
def customer_calls(
    request: Request,
    customer_id: str,
    list: str | None = Query(default=None),
    db: Session = Depends(get_db)
):
    print("List calls")    
    # Capture all query parameters as a dict
    query_params = dict(request.query_params)

    calls = db.query(Call).filter(Call.caller_id == int(customer_id)).all()

    return templates.TemplateResponse(
        "calls/call_log.html",
        {"request": request, "calls": calls},
    )

@router.get("/", response_class=HTMLResponse, name="products_list")
def products_list(
    request: Request,
    filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = select(Product)
    if filter:
        query = query.where(Product.name.contains(filter))
    products = db.execute(query).scalars().all()
    return templates.TemplateResponse(
        "products/list.html", {"request": request, "products": products}
    )


## Get number to call

@router.get("/number", response_class=HTMLResponse, name="number")
def number(
    request: Request,
    filter: Optional[str] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    
    return templates.TemplateResponse(
        "calls/number.html", {"request": request, "user": user}
    )



# ---------------------------
# Call Details
# ---------------------------


@router.get("/call/{call_id}", response_class=HTMLResponse)
def call_details(
    request: Request,
    call_id: str,
    db: Session = Depends(get_db)
):
    
    call = db.query(Call).filter(Call.id == int(call_id)).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    call = (
        db.query(Call)
        .filter(Call.id == call_id)
        .first()
    )

    return templates.TemplateResponse(
        "calls/info.html",
        {
            "request": request, 
            "call": call, 
            "call_id": call_id, 
        }
    )


# ---------------------------
# Update Customer Call Data
# ---------------------------

from models.models import Update
from models.models import Call, CallUpdate
from core.functions.helpers import populate
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError



@router.post("/call/save", name="save_call", response_class=HTMLResponse)
async def save_call(
    request: Request,
    update_data: Update,
    comment: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    
    product_id = update_data.product_id
    product_status = getattr(update_data, "product_status", None)
    product_type_status = getattr(update_data, "product_type_status", None)
    customer_id = update_data.customer_id
    status = getattr(update_data, "status", None)
    call_id = getattr(update_data, "call_id", None)


    # update customer comment
    customer_comment = getattr(update_data, "customer_comment", None)
    customer = db.query(Customer).filter_by(
        id=customer_id
    ).first()
    customer.comment = customer_comment

    if (status == "1" or status == "3"): #1 and 3 is hardcoded for answer/extrnal
        # Ensure extra is a dict
        if customer.extra is None:
            customer.extra = {}
        customer.last_call_date = datetime.now(timezone.utc)

    db.commit()
    db.refresh(customer)

    # save Alarm if product_alarm_date
    product_alarm_date = getattr(update_data, "product_alarm_date", None)
    alarm_note = getattr(update_data, "alarm_note", "")

    if product_alarm_date:
        try:
            naive_dt = datetime.strptime(product_alarm_date, "%Y-%m-%dT%H:%M")
            product_alarm_date = naive_dt.astimezone(timezone.utc)            
        except ValueError:
            product_alarm_date = datetime.now(timezone.utc)

        event_alarm_reminder_minutes = int(getattr(update_data, "event_alarm_reminder", 30))
        event_alarm_reminder = product_alarm_date - timedelta(minutes=event_alarm_reminder_minutes)

        # Try to find existing alarm for this user & customer
        alarm = (
            db.query(Alarm)
            .filter_by(customer_id=customer_id, caller_id=user.caller_id, product_id=product_id)
            .first()
        )

        if not alarm:
            alarm = Alarm(customer_id=customer_id, caller_id=user.caller_id)
            db.add(alarm)
        else:
            print(f"Alarm found: {alarm.id}")

        # Update shared fields
        alarm.date = product_alarm_date
        alarm.reminder = event_alarm_reminder
        alarm.reminder_sent =  None
        alarm.note = alarm_note
        alarm.extra = alarm.extra or {}
        alarm.product_id = product_id

        try:
            db.commit()
            db.refresh(alarm)
            print(f"Alarm saved successfully: {alarm.id}")
        except Exception as e:
            db.rollback()
            print("Failed to save alarm:", e)



    # Get the CustomerProduct match
    product_customer = db.query(ProductCustomer).filter_by(
        customer_id=customer_id, product_id=product_id
    ).first()

    # Check if product_customer exists
    if (product_id and product_status):
        if not product_customer:
            print("No existing ProductCustomer found. Creating a new one.")
            product_customer = ProductCustomer(
                customer_id=customer_id,
                product_id=product_id
            )
        else:
            print("Found existing ProductCustomer:", product_customer)

        # Update status
        product_customer.status = product_status
        product_customer.type_status = product_type_status
        print("Setting ProductCustomer.type_status =", product_type_status)

        # Add to DB and commit
        db.add(product_customer)
        try:
            db.commit()
        except Exception as e:
            db.rollback()

    # Try to fetch existing call by ID if provided
    existing_call = None
    if isinstance(call_id, str):
        existing_call = db.query(Call).filter_by(id=call_id).first()

    print ("callid", call_id)
    if(existing_call):
        print("exist")
    if (status):
        # Use existing call or create new one
        call = existing_call or Call()

        # Populate DB model dynamically
        try:
            call = populate(update_data.model_dump(exclude_unset=True), call, CallUpdate)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())

        # Set call_date for new calls
        if not existing_call:
            call.call_date = datetime.now(timezone.utc)
            call.id = None  # let DB auto-generate if using Integer PK
            db.add(call)

        # set caller_id from logged in user
        call.caller_id = user.caller_id

        if (not call.note):
            call.note=""

        try:
            db.commit()
            db.refresh(call)
        except IntegrityError:
            db.rollback()
            raise

    if (status):
        responce = JSONResponse(content={"detail": "Saved", "call_id": call.id})
    else:
        responce = JSONResponse(content={"detail": "Saved"})

    if (product_alarm_date):
        responce.headers["HX-Trigger"] = "alarmsReload"
    return responce

# Autogenerated

# ---------------------------
# Select a Customer for Call Center
# ---------------------------
@router.get("/select/{customer_id}", response_class=HTMLResponse)
def select_customer(customer_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Select a customer (e.g., open their detail view in dashboard).

    """

    customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()
    if not customer:
        return HTMLResponse("<div>Customer not found</div>", status_code=404)

    return templates.TemplateResponse(
        "calls/customer_detail.html",
        {"request": request, "customer": customer},
    )


# ---------------------------
# Customer Info Fragment
# ---------------------------
@router.get("/customer/{customer_id}/info", response_class=HTMLResponse, name="calls.customer_info")
def customer_info(customer_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Return HTMX fragment with customer details.
    """
    customer = db.query(Customer).filter(Customer.id == int(customer_id)).first()
    if not customer:
        return HTMLResponse("<div>Customer not found</div>", status_code=404)

    return templates.TemplateResponse(
        "calls/customer_info.html",
        {"request": request, "customer": customer},
    )

# ---------------------------
# Call Info Fragment
# ---------------------------
@router.get("/calls/{call_id}/info", response_class=HTMLResponse, name="calls.call_info")
def call_info(call_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Return HTMX fragment with call details.
    """
    call = db.query(Call).filter(Call.id == int(call_id)).first()
    if not call:
        return HTMLResponse("<div>Customer not found</div>", status_code=404)

    return templates.TemplateResponse(
        "calls/call_info.html",
        {"request": request, "call": call},
    )


# ---------------------------
# Customer Call Log Fragment
# ---------------------------
@router.get("/customer/{customer_id}/calls", response_class=HTMLResponse)
def customer_call_log(customer_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Return HTMX fragment with a customer's call history.
    """
    calls = (
        db.query(models.Call)
        .filter(models.Call.customer_id == customer_id)
        .order_by(models.Call.timestamp.desc())
        .all()
    )

    return templates.TemplateResponse(
        "calls/fragments/customer_calls.html",
        {"request": request, "calls": calls, "customer_id": customer_id},
    )


# ---------------------------
# List Customer Products Fragment
# ---------------------------
@router.get("/customer/{customer_id}/products", response_class=HTMLResponse)
def list_customer_products(customer_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Return HTMX fragment with all products associated with a customer.
    """
    products = (
        db.query(models.CustomerProduct)
        .filter(models.CustomerProduct.customerId == customer_id)
        .all()
    )

    return templates.TemplateResponse(
        "calls/fragments/customer_products.html",
        {"request": request, "products": products, "customer_id": customer_id},
    )


# -----------------------------
# Product Detail Modal (HTMX fragment)
# -----------------------------
@router.get("/product/{product_id}", response_class=HTMLResponse)
def calls_product_detail(
    request: Request,
    product_id: int,
    customer_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        

    # Get the ProductCustomer match
    product_customer = db.query(ProductCustomer).filter_by(
        customer_id=customer_id, product_id=product_id
    ).first()


    product_status = None
    product_type_status = None
    if product_customer:
        product_status = product_customer.status
        product_type_status = product_customer.type_status

    return templates.TemplateResponse(
        "calls/product_info.html",
        {
            "request": request, 
            "product": product, 
            "product_status": product_status,
            "product_type_status": product_type_status,
            "products_map": constants.products_map,
        }
    )

from fastapi import WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
import json

# Secret key for JWT
JWT_SECRET_KEY = "supersecret-jwt-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    token = websocket.query_params.get("token")
    print("Received token:", token)    
    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        print("Payload:", payload)
        user_id = payload.get("sub")
        if not user_id:
            raise JWTError()
    except JWTError as e:
        print("JWTError:", e)
        await websocket.close(code=1008)
        return

    print("User ID", user_id)


    if user_id not in active_connections:
        active_connections[user_id] = []
        user_data[user_id] = {"user_id": user_id}

    active_connections[user_id].append(websocket)

    # Send initial value
    await websocket.send_json(user_data[user_id])

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            payload = json.loads(data)
            print(f"Recieved data {data}")  
            # Respond with "pong"
#            await websocket.send_json("pong")
            call = payload.get("call")
            number = payload.get("number")
            if call:
                print(f"Call")

                for ws in active_connections.get(user_id, []):
                    try:
                        print("Sending to web sockets")
                        await ws.send_json({ "call": "true", "number": number })

                    except RuntimeError:
                        # WebSocket is closed, mark for removal
                        to_remove.append(ws)
                
    except WebSocketDisconnect:
        active_connections[user_id].remove(websocket)
        if not active_connections[user_id]:
            del active_connections[user_id]
            del user_data[user_id]
