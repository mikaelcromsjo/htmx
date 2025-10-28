# admin.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi import APIRouter, Depends, Form, Request, HTTPException, Query

from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Column, Integer, String, DateTime, JSON, select
from sqlalchemy.orm import Session, declarative_base
from typing import Optional
from datetime import datetime
from datetime import date
from sqlalchemy import select, and_
from datetime import date, timedelta
from core.auth import get_current_user
import subprocess, shlex
from typing import List, Optional
from core.models.base import Base
from pydantic import BaseModel
from pydantic import BaseModel, Field

from datetime import datetime

from core.database import get_db   
from templates import templates
from core.database import engine
from core.models.base import Base
from models.models import Update
from core.functions.helpers import populate

import subprocess

router = APIRouter(prefix="/admin", tags=["admin"])

# Whitelist of scripts admins can run
ALLOWED_SCRIPTS = {
    "manage_users": "/app/backend/scripts/manage_users.py",
    "cleanup_logs": "/app/backend/scripts/cleanup_logs.py",
}


@router.get("/script", response_class=HTMLResponse)
async def admin_script(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if user.admin <= 0:
        return HTMLResponse("Access denied", status_code=403)

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "output": None, "scripts": ALLOWED_SCRIPTS},
    )


def clean_output(raw_output: str) -> str:
    """Remove noisy PYTHONPATH and warnings for nicer display."""
    # Drop Python path and site-packages lines
    lines = raw_output.splitlines()
    cleaned = []
    for line in lines:
        if any(keyword in line for keyword in [
            "PYTHONPATH",
            "/usr/local/lib/python",
            "site-packages",
            "UserWarning",
        ]):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


@router.get("/script", response_class=HTMLResponse)
async def admin_script(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if user.admin <= 0:
        return HTMLResponse("Access denied", status_code=403)

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "output": None, "scripts": ALLOWED_SCRIPTS},
    )


@router.post("/script", response_class=HTMLResponse)
async def run_admin_script(
    request: Request,
    script_name: str = Form(...),
    args: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if user.admin <= 0:
        return HTMLResponse("Access denied", status_code=403)

    if script_name not in ALLOWED_SCRIPTS:
        return HTMLResponse("Invalid script", status_code=400)

    script_path = ALLOWED_SCRIPTS[script_name]

    try:
        arg_list = shlex.split(args) if args.strip() else ["--help"]
        command = ["python", script_path] + arg_list

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=20,
        )

        raw_output = (result.stdout or "") + (result.stderr or "")
        output = clean_output(raw_output)
        output += f"\n\n[exit code: {result.returncode}]"

    except Exception as e:
        output = f"⚠️ Error running script: {e}"

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "output": output, "scripts": ALLOWED_SCRIPTS},
    )


# -----------------------------
# List Dashboard (HTMX fragment)
# -----------------------------
@router.get("/", response_class=HTMLResponse, name="admin_dashboard")
def admin_dashboard(
    request: Request,
    filter: Optional[str] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    
    

    return templates.TemplateResponse(
        "admin/dashboard.html", {"request": request, "user": user, "scripts": ALLOWED_SCRIPTS}
    )