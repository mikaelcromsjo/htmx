import csv
from io import StringIO
from fastapi import UploadFile, Form, File
from models.models import Customer, Call, Event, Caller
from core.functions.helpers import formatPhoneNr
import json
from typing import List, Union

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
    "stats": "/app/backend/scripts/generate_stats.py",
    "test_data": "/app/backend/scripts/generate_test_data.py",
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
        "admin/script.html",
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
        "admin/script.html",
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
        output = f"Running {script_name} {args}\n\n"
        output += clean_output(raw_output)
        output += f"\n\n[exit code: {result.returncode}]"

    except Exception as e:
        output = f"Running {script_name} {args}\n\n"
        output += f"⚠️ Error running script: {e}"

    return templates.TemplateResponse(
        "admin/script.html",
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
        "admin/dashboard.html", {"request": request }
    )


@router.get("/script", response_class=HTMLResponse, name="admin_script")
def admin_script(
    request: Request,
    filter: Optional[str] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    

    return templates.TemplateResponse(
        "admin/script.html", {"request": request, "user": user, "scripts": ALLOWED_SCRIPTS}
    )

import json

def create_customer_from_row(row: dict, db):
    """
    Create a new Customer instance from a row dict.
    Safely handles missing, boolean, and JSON fields.
    """

    def _parse_json_field(value):
        """Parse JSON-like fields (list or dict), return default if invalid."""
        import json
        if not value:
            return []
        if isinstance(value, (list, dict)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return []

    def _parse_bool(value):
        """Convert various truthy strings to bool."""
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in ["true", "1", "yes", "y", "t"]

    def _parse_tags(value):
        """Comma-separated tags"""
        if not value:
            return []
        return [v.strip().strip('"').strip("'") for v in value.split(",") if v.strip()]

    def _parse_id_list(value):
        """
        Parse CSV field into a list of string IDs.
        Accepts:
        - JSON array: '["1","2","3"]' or '[1,2,3]'
        - Comma-separated list: '1,2,3'
        - Single ID: '5'
        - Empty/None -> []
        Returns: list of strings, e.g. ["1", "2", "3"]
        """
        if not value:
            return []

        # Already a list or tuple
        if isinstance(value, (list, tuple)):
            return [str(v).strip() for v in value if str(v).strip()]

        s = str(value).strip()
        if not s:
            return []

        # Try JSON decode
        try:
            parsed = json.loads(s)
            if isinstance(parsed, (list, tuple)):
                return [str(v).strip() for v in parsed if str(v).strip()]
            elif parsed is not None:
                return [str(parsed).strip()]
            return []
        except Exception:
            # Fallback to comma-separated list
            parts = [p.strip() for p in s.split(",") if p.strip()]
            return [str(p) for p in parts]
            
# --- Caller handling ---
    caller = None
    caller_name = row.get("caller_name")
    if caller_name:
        caller_name = caller_name.strip()
        if caller_name:
            caller = db.query(Caller).filter(Caller.name == caller_name).first()
            if not caller:
                caller = Caller(name=caller_name)
                db.add(caller)
                db.commit()
                db.refresh(caller)

    new_customer = Customer(
        user_id=row.get("user_id") or "",
        first_name=row.get("first_name", "").strip(),
        last_name=row.get("last_name", "").strip(),
        code_name=_parse_bool(row.get("code_name")),
        email=row.get("email"),
        phone=formatPhoneNr(row.get("phone")),
        description_phone=row.get("description_phone"),
        location=row.get("location"),
        contributes=int(row.get("contributes") or 0) or None,
        previous_caller=_parse_json_field(row.get("previous_caller")),
        previous_categories=_parse_json_field(row.get("previous_categories")),
        comment=row.get("comment"),
        sub_caller=row.get("sub_caller"),
        organisations=_parse_id_list(row.get("organisations")),
        categories=_parse_id_list(row.get("categories")),
        personality_type=int(row.get("personality_type") or 0) or None,
        controlled=_parse_bool(row.get("controlled")),
        filter_a=_parse_bool(row.get("filter_a")),
        filter_b=_parse_bool(row.get("filter_b")),
        filter_c=_parse_bool(row.get("filter_c")),
        filter_d=_parse_bool(row.get("filter_d")),
        filter_e=_parse_bool(row.get("filter_e")),
        filter_f=_parse_bool(row.get("filter_f")),
        filter_g=_parse_bool(row.get("filter_g")),
        filter_h=_parse_bool(row.get("filter_h")),
        tags=_parse_tags(row.get("tags")),
        extra=row.get("extra") if isinstance(row.get("extra"), dict) else {},
         # --- Caller link ---
        caller_id=caller.id if caller else None,
        caller=caller,        
    )

    return new_customer

@router.get("/import", response_class=HTMLResponse, name="admin_import")
def admin_import(
    request: Request,
):

    return templates.TemplateResponse(
        "admin/import.html", {"request": request }
    )

@router.post("/import", response_class=HTMLResponse)
async def import_customers(
    request: Request,
    csv_text: str = Form(""),
    csv_file: UploadFile = File(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    content = ""

    # 1️⃣ Read content from either upload or text
    if csv_file:
        content = (await csv_file.read()).decode("utf-8")
    elif csv_text.strip():
        content = csv_text.strip()
    else:
        return templates.TemplateResponse(
            "partials/message.html",
            {"request": request, "message": "No CSV data provided."},
        )

    # 2️⃣ Parse CSV
    reader = csv.DictReader(StringIO(content))
    added, duplicates = [], []

    for row in reader:
        phone = formatPhoneNr(row.get("phone", ""))
        if not phone:
            continue

        existing = db.query(Customer).filter(Customer.phone == phone).first()
        if existing:
            duplicates.append(phone)
            continue

        # Create new customer record
        new_customer = create_customer_from_row(row, db)

        db.add(new_customer)
        added.append(phone)

    db.commit()

    # 3️⃣ Return summary (render partial)
    summary_html = f"""
    <div class='p-2 bg-gray-100 rounded'>
      <p><strong>Added:</strong> {len(added)} customers</p>
      <p><strong>Duplicates skipped:</strong> {len(duplicates)}</p>
      {("<p>Duplicate phones:</p><ul>" + "".join(f"<li>{p}</li>" for p in duplicates) + "</ul>") if duplicates else ""}
    </div>
    """
    return HTMLResponse(summary_html)

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from pathlib import Path
import json
import importlib
import data.constants as constants  # Your preloaded data

DATA_DIR = Path("./data")

def save_json(filename, data):
    path = DATA_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@router.get("/data", response_class=HTMLResponse, name="admin_data")
def admin_data(request: Request):
    """Display current JSON data in editable textareas."""
    return templates.TemplateResponse(
        "admin/data.html",
        {
            "request": request,
            "categories_json": json.dumps(constants.categories, indent=2, ensure_ascii=False),
            "organisations_json": json.dumps(constants.organisations, indent=2, ensure_ascii=False),
            "filters_json": json.dumps(constants.filters, indent=2, ensure_ascii=False),
            "personalities_json": json.dumps(constants.personalities, indent=2, ensure_ascii=False),
        },
    )


@router.post("/data", response_class=HTMLResponse)
def save_data(
    request: Request,
    categories_text: str = Form(...),
    organisations_text: str = Form(...),
    filters_text: str = Form(...),
    personalities_text: str = Form(...),
):
    """Save edited JSON, then reload data.constants."""
    try:
        new_categories = json.loads(categories_text)
        new_organisations = json.loads(organisations_text)
        new_filters = json.loads(filters_text)
        new_personalities = json.loads(personalities_text)
    except json.JSONDecodeError as e:
        return HTMLResponse(
            f"<div class='alert alert-danger'>Invalid JSON: {e}</div>", status_code=400
        )

    # Save to disk
    save_json("categories.json", new_categories)
    save_json("organisations.json", new_organisations)
    save_json("filters.json", new_filters)
    save_json("personalities.json", new_personalities)

    # Reload constants (this will rebuild the *_map variables)
    importlib.reload(constants)

    return templates.TemplateResponse(
        "admin/data.html",
        {
            "request": request,
            "categories_json": json.dumps(constants.categories, indent=2, ensure_ascii=False),
            "organisations_json": json.dumps(constants.organisations, indent=2, ensure_ascii=False),
            "filters_json": json.dumps(constants.filters, indent=2, ensure_ascii=False),
            "personalities_json": json.dumps(constants.personalities, indent=2, ensure_ascii=False),
            "message": "✅ Data saved and reloaded successfully!",
        },
    )
