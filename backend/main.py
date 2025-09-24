# main.py
"""
Entrypoint for the FastAPI + HTMX + Alpine.js prototype application.

Features:
- SQLite database with SQLAlchemy ORM
- Jinja2 template rendering
- Static file serving
- Modular routers for customers, events, calls, alarms
- One-page style app (HTMX returns fragments into a container)
"""




from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.responses import HTMLResponse, Response

from starlette.types import ASGIApp, Scope, Receive, Send
from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.models.base import Base
from models.models import Alarm, Customer, Event

from core.database import engine
from core.auth import get_current_user
from core.database import get_db, init_admin_user
from sqlalchemy.orm import relationship, Session


import logging
from sqlalchemy import inspect

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from jose import jwt, JWTError
from datetime import datetime, timedelta

from core.models.models import BaseMixin, Update, User

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # points to /app/backend


SESSION_SECRET = "super-secret-key"
JWT_SECRET_KEY = "supersecret-jwt-key" # dublicated in calls.py TODO
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI app setup ---
app = FastAPI(title="HTMX + Alpine.js Prototype", debug=True)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)


# Function to list tables
def list_tables():
    inspector = inspect(engine)
    return inspector.get_table_names()

# Function to list all models registered with Base
def list_models():
    # Returns names of all mapped classes
    return [mapper.class_.__name__ for mapper in Base.registry.mappers]

# Startup event
@app.on_event("startup")
def on_startup():

    # Check DB connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✅ Database connected successfully.")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return

    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created (if missing).")

    logger.info("Default Admin created (if missing).")
    init_admin_user()

    # Print existing tables
    tables = list_tables()
    logger.info(f"Tables currently in DB: {tables}")

    # Print all models registered with Base
    models = list_models()
    logger.info(f"Models registered with Base: {models}")


# Static files (CSS, JS, images) will be served from /static
app.mount("/static", StaticFiles(directory="core/static"), name="static")

# Jinja2 templates (HTML pages/fragments)
from templates import templates

from state import user_data, active_connections

# --- Routers ---
# Routers should be defined in /routers/*.py and included here.
# Each router file exposes a "router" object.
from routers import customers, events, calls, alarms, callers

app.include_router(customers.router, tags=["customers"])
app.include_router(events.router, tags=["events"])
app.include_router(calls.router, tags=["calls"])
app.include_router(alarms.router, tags=["alarms"])
app.include_router(callers.router, tags=["callers"])


from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

@app.get("/login")
async def login_get(request: Request):
    # If already logged in, redirect to home
    if request.session.get("authenticated"):
        return RedirectResponse(url="/")
    return templates.TemplateResponse("login.html", {"request": request})

# --- Routes ---
@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):


    user = db.query(User).filter(User.username == username).first()
    if user and user.verify_password(password):
        request.session["authenticated"] = True
        request.session["admin"] = user.admin
        request.session["user"] = user.username
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})


@app.get("/get-ws-token")
def get_ws_token(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode({"sub": user, "exp": expire}, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return {"ws_token": token}


# Logout route
@app.get("/logout") #not secure
@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"message": "Logged out"})


@app.post("/users/create")
async def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    caller_id: int = Form(None),
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)

    # --- Admin-only check ---
    if not current_user.admin:
        raise HTTPException(status_code=403, detail="Only admins can create users")

    # --- Create new user ---
    new_user = User(username=username, caller_id=caller_id)
    new_user.set_password(password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": f"User {username} created successfully", "user_id": new_user.id}


# Root route: check if logged in
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):

    user = request.session.get("user")  # optional, might be None
    if user:
        # Already logged in → redirect to dashboard
        return RedirectResponse(url="/dashboard")
    else:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
            },
        )


# --- Root route ---
@app.get("/dashboard", response_class=HTMLResponse, )
async def read_root(request: Request, user: str = Depends(get_current_user)):
    """
    Render the base page with a placeholder container.
    HTMX will dynamically swap content into this container.
    """
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "Dashboard",
            "user": user.username,
            "caller": user.caller.name,
        },
    )

# --- Dependency for DB session (to be imported in routers) ---
def get_db():
    """
    Provides a SQLAlchemy session per request.
    Usage in routes: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()







# --- Main entrypoint ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
