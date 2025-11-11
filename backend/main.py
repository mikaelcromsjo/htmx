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


from starlette.middleware.base import BaseHTTPMiddleware

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

from core.lang import get_translator


import logging
from sqlalchemy import inspect

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from jose import jwt, JWTError
from datetime import datetime, timedelta
from core.functions.helpers import local_to_utc, utc_to_local


from core.models.models import BaseMixin, Update, User
from threading import Lock
# core/scheduler.py
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.models import Alarm
from core.database import SessionLocal
from sqlalchemy import func, or_, and_
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


async def alarm_scheduler():
    logger.info("✅ Alarm.")
    """Periodically check for alarms and send them via WebSocket."""
    while True:
        await asyncio.sleep(60)  # adjust interval as needed

        db: Session = SessionLocal()
        now = datetime.now(timezone.utc)
        logger.info(f"Scheduler running at {now.isoformat()} utc")
        try:
            due_alarms = (
                db.query(Alarm)
                .filter(Alarm.date >= now)  # event not passed
                .filter(
                    or_(
                        # First reminder: send only if reminder time reached and not yet sent
                        and_(
                            Alarm.reminder <= now,           # current time reached reminder
                            Alarm.reminder_sent.is_(None)    # first reminder not sent
                        ),

                        # Second reminder: 30 minutes before event, only if first reminder sent
                        and_(
                            Alarm.date - timedelta(minutes=30) <= now,     # 30 min before event
                            Alarm.reminder_sent.isnot(None),               # first reminder already sent
                            Alarm.reminder_sent < (Alarm.date - timedelta(minutes=30))  # second reminder not sent yet
                        )
                    )
                )
                .all()
            )

            for alarm in due_alarms:

                caller_id = alarm.caller_id
                users = db.query(User).filter(User.caller_id == caller_id).all()

                for user in users:

                    if not user:
                        continue
                
                    logger.info("✅ Send Alarm.")

                    payload = {
                        "type": "alarm",
                        "customer": f"{alarm.customer.first_name} {alarm.customer.last_name}",
                        "note": alarm.note,
                        "date": alarm.date.isoformat(),
                    }

                    for ws in active_connections.get(str(user.id), []):
                        try:
                            await ws.send_json(payload)
                            alarm.reminder_sent = now
                            db.commit()
                        except Exception as e:
                            print(f"WebSocket send failed for {user.id}: {e}")


        except Exception as e:
            print("Scheduler error:", e)
        finally:
            db.close()



import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # points to /app/backend


SESSION_SECRET = "super-secret-key"
JWT_SECRET_KEY = "supersecret-jwt-key" # dublicated in calls.py TODO
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1
SUPPORTED_LANGUAGES = ["sv"]


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_translators_cache = {}
_cache_lock = Lock()

def get_translator_cached(lang_code: str):
    """Return a translator for lang_code, caching it globally."""
    # Use lock for thread safety
    with _cache_lock:
        if lang_code not in _translators_cache:
            _translators_cache[lang_code] = get_translator(lang_code)
        return _translators_cache[lang_code]

# --- FastAPI app setup ---
app = FastAPI(title="HTMX + Alpine.js Prototype", debug=True)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Only return the error message, no traceback
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401:
        # Don't redirect if already on login/logout
        if request.url.path not in ["/login", "/logout"]:
            return RedirectResponse(url="/login", status_code=303)
    raise exc


class LanguageMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            from starlette.requests import Request
            request = Request(scope, receive=receive)


            # Get lang_code from session or recreate it
            lang_code = request.session.get("lang_code")
            if not lang_code:
                accept_language = request.headers.get("accept-language", "")
                lang_code = get_best_language_match(accept_language, SUPPORTED_LANGUAGES)
                request.session["lang_code"] = lang_code

            # Load translator from cache (thread-safe)
            templates.env.filters["t"] = get_translator_cached(lang_code)

        await self.app(scope, receive, send)

# Add the middleware AFTER SessionMiddleware
app.add_middleware(LanguageMiddleware)


app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="session",
    https_only=True,
)

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
    init_admin_user()
    logger.info("✅ Set up Alarms.")
    asyncio.create_task(alarm_scheduler())


# Static files (CSS, JS, images) will be served from /static
app.mount("/static", StaticFiles(directory="core/static"), name="static")

# Jinja2 templates (HTML pages/fragments)
from templates import templates
from state import user_data, active_connections

# --- Routers ---
# Routers should be defined in /routers/*.py and included here.
# Each router file exposes a "router" object.
from routers import customers, events, calls, alarms, callers, user, invoices, companies, alarms, admin, tags

app.include_router(tags.router, tags=["tags"])
app.include_router(customers.router, tags=["customers"])
app.include_router(events.router, tags=["events"])
app.include_router(calls.router, tags=["calls"])
app.include_router(alarms.router, tags=["alarms"])
app.include_router(callers.router, tags=["callers"])
app.include_router(user.router, tags=["user"])
app.include_router(invoices.router, tags=["invoices"])
app.include_router(companies.router, tags=["companies"])
app.include_router(alarms.router, tags=["alarms"])
app.include_router(admin.router, tags=["admin"])


from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

templates.env.filters["date"] = utc_to_local
templates.env.globals["now"] = datetime.utcnow
templates.env.globals["timedelta"] = timedelta

@app.get("/login")
async def login_get(request: Request):
        
    return templates.TemplateResponse("login.html", {"request": request})

# --- Routes ---
@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):

    lang_code = request.cookies.get("lang_code")
    if not lang_code:
        accept_language = request.headers.get("accept-language", "")
        lang_code = get_best_language_match(accept_language, SUPPORTED_LANGUAGES)


#    with _cache_lock:
#        _translators_cache.clear()
#        for lang in SUPPORTED_LANGUAGES:
#            _translators_cache[lang_code] = get_translator(lang)
#        templates.env.filters["t"] = get_translator_cached(lang)

    user = db.query(User).filter(User.username == username).first()
    if user and user.verify_password(password):
        request.session["authenticated"] = True
        request.session["admin"] = user.admin
        request.session["user"] = user.id
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})


@app.get("/get-ws-token")
def get_ws_token(request: Request):
    user = str(request.session.get("user"))
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode({"sub": user, "exp": expire}, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return {"ws_token": token}

# Logout route
@app.get("/logout")
@app.post("/logout")
async def logout(request: Request):

    request.session.clear()
    _translators_cache.clear()

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "message": "Logged out" 
        },
    )


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
async def root(request: Request, user = Depends(get_current_user)):

    lang_code = request.cookies.get("lang_code")
    if not lang_code:
        accept_language = request.headers.get("accept-language", "")
        lang_code = get_best_language_match(accept_language, SUPPORTED_LANGUAGES)

    templates.env.filters["t"] = get_translator_cached(lang_code)

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
            "is_admin": user.admin,
            "caller": getattr(user.caller, "name", ""),
        },
    )


def get_best_language_match(accept_language: str, supported: list[str]) -> str:
    if not accept_language:
        return supported[0]  # default to first supported language

    # Split and sort by quality factor (q=)
    languages = accept_language.split(",")
    parsed = []
    for lang in languages:
        parts = lang.strip().split(";")
        code = parts[0].strip().split("-")[0]  # only use base language like "sv" from "sv-SE"
        q = 1.0  # default quality
        if len(parts) > 1 and parts[1].startswith("q="):
            try:
                q = float(parts[1][2:])
            except ValueError:
                pass
        parsed.append((code, q))

    # Sort by quality factor descending
    parsed.sort(key=lambda x: x[1], reverse=True)

    # Return first match from supported languages
    for code, _ in parsed:
        if code in supported:
            return code

    return supported[0]  # fallback






# --- Main entrypoint ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
