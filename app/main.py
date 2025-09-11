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
from fastapi import WebSocket

from starlette.types import ASGIApp, Scope, Receive, Send
from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.models import Alarm, Customer, Event

from app.database import engine
from app.auth import get_current_user

import logging
from sqlalchemy import inspect

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI app setup ---
app = FastAPI(title="HTMX + Alpine.js Prototype", debug=True)
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

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

    # Print existing tables
    tables = list_tables()
    logger.info(f"Tables currently in DB: {tables}")

    # Print all models registered with Base
    models = list_models()
    logger.info(f"Models registered with Base: {models}")


# Static files (CSS, JS, images) will be served from /static
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Jinja2 templates (HTML pages/fragments)
from app.templates import templates

from app.state import user_data, active_connections

# --- Routers ---
# Routers should be defined in /routers/*.py and included here.
# Each router file exposes a "router" object.
from app.routers import customers, events, calls, alarms, callers

app.include_router(customers.router, tags=["customers"])
app.include_router(events.router, tags=["events"])
app.include_router(calls.router, tags=["calls"])
app.include_router(alarms.router, tags=["alarms"])
app.include_router(callers.router, tags=["callers"])


# Login route
@app.get("/login") #not secure
@app.post("/login")
async def login(request: Request):
    # Example: in real apps, validate username/password here
    user = "Alice"
    request.session["authenticated"] = True
    request.session["user"] = user
    response = Response()
    response.headers["HX-Refresh"] = "true"
    return response

# Logout route
@app.get("/logout") #not secure
@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"message": "Logged out"})

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
            "user": user,
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

# WebSocket endpoint (receiver browsers connect here)
@app.websocket("/ws/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # For demo purposes, we assume a single user "alice"
    user = "Alice"

    if user not in active_connections:
        active_connections[user] = []
        user_data[user] = {"customer_id": 0}

    active_connections[user].append(websocket)

    # Send initial value
    await websocket.send_json(user_data[user])

    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections[user].remove(websocket)
        if not active_connections[user]:
            del active_connections[user]
            del user_data[user]

# --- Main entrypoint ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
