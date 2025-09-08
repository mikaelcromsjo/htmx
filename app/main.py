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

from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import engine
from app.models.base import Base
from app.models.models import Alarm, Customer, Event

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



# --- Routers ---
# Routers should be defined in /routers/*.py and included here.
# Each router file exposes a "router" object.
from app.routers import customers, events, calls, alarms, callers

app.include_router(customers.router, tags=["customers"])
app.include_router(events.router, tags=["events"])
app.include_router(calls.router, tags=["calls"])
app.include_router(alarms.router, tags=["alarms"])
app.include_router(callers.router, tags=["callers"])


# --- Root route ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Render the base page with a placeholder container.
    HTMX will dynamically swap content into this container.
    """
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": "Dashboard",
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
