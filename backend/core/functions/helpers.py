from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
import os
from zoneinfo import ZoneInfo  # Python 3.9+
import data.constants as constants

from typing import Type
from typing import Any, Union

from pydantic import BaseModel

from templates import templates
from sqlalchemy import func, or_, and_

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB

def populate(update_dict: dict, db_obj: Any, pyd_model: Type[BaseModel]) -> Any:
    """
    Convert a raw dict (from Update) to a Pydantic model, then populate the DB model.
    Handles:
      - Empty strings for numeric/optional fields
      - list -> "a,b" if field is str or Optional[str]
      - dict -> JSON string if field is str or Optional[str]
    """
    import json
    from typing import Union, get_origin, get_args

    preprocessed = {}

    for field_name, value in update_dict.items():
        field_info = pyd_model.model_fields.get(field_name)
        if not field_info:
            continue

        field_type = field_info.annotation
        origin = get_origin(field_type)
        args = get_args(field_type)

        # --- Handle Optional[T] ---
        if origin is Union and type(None) in args:
            base_type = next((a for a in args if a is not type(None)), str)
        else:
            base_type = field_type

        # --- Handle empty strings → None for numeric/optional ---
        if value == "" and (base_type in (int, float, bool) or (origin is Union and type(None) in args)):
            preprocessed[field_name] = None
            continue

        # --- Handle list → comma-joined string if base_type is str ---
        if base_type == str and isinstance(value, list):
            cleaned = [str(v).strip() for v in value if str(v).strip() != ""]
            preprocessed[field_name] = ",".join(cleaned)
            continue

        # --- Handle dict → JSON string if base_type is str ---
        if base_type == str and isinstance(value, dict):
            preprocessed[field_name] = json.dumps(value, ensure_ascii=False)
            continue

         # --- Handle checkbox-style list for booleans ---
        if base_type == bool and isinstance(value, list):
            # Keep the last value if multiple provided
            last_val = str(value[-1]).lower().strip()
            preprocessed[field_name] = last_val in ("true", "1", "on", "yes")
            continue        

        # Default: pass through
        preprocessed[field_name] = value

    # --- Validate and coerce using Pydantic ---
    pyd_instance = pyd_model(**preprocessed)

    # --- Populate the DB object ---
    for field_name, value in pyd_instance.model_dump(exclude_unset=True).items():
        setattr(db_obj, field_name, convert_value_for_field(pyd_instance, field_name, value))

    return db_obj


def convert_value_for_field(pyd_instance: BaseModel, field_name: str, value: Any):
    """
    Convert value to correct type based on Pydantic field type.
    Handles Optional[T], list/dict, and str coercion properly.
    """
    from typing import get_origin, get_args, Union
    import json

    field_type = pyd_instance.model_fields[field_name].annotation
    origin = get_origin(field_type)
    args = get_args(field_type)

    # Handle Optional[T]
    if origin is Union and type(None) in args:
        target_type = next((a for a in args if a is not type(None)), str)
        value = _convert_value(target_type, value) if value not in ("", None) else None
    else:
        value = _convert_value(field_type, value)

    # If Pydantic expects str but got list/dict, force conversion
    if value is not None and (field_type == str or (origin is Union and str in args)):
        if isinstance(value, list):
            value = ",".join(map(str, value))
        elif isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False)

    return value


def _convert_value(field_type, value):
    """Internal helper for safe type conversion."""
    from typing import get_origin
    import json

    origin = get_origin(field_type)

    if value is None:
        return None

    if field_type == int:
        return int(value)
    if field_type == float:
        return float(value)
    if field_type == bool:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)
    if field_type == str:
        if isinstance(value, list):
            return ",".join(map(str, value))
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
    if origin == list:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return [v.strip() for v in value.split(",") if v.strip()]
        return list(value)
    if origin == dict:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {}
        return dict(value)

    return value


def render(template_name: str, context: dict, base_template: str = "base.html"):
    request = context.get("request")
    if request is None:
        raise ValueError("context must include 'request'")

    template_name = template_name.lstrip("/")
    base_template = base_template.lstrip("/")

    if request.headers.get("hx-request"):
        return templates.TemplateResponse(template_name, context)
    else:
        ctx = context.copy()
        ctx["content_template"] = template_name
        return templates.TemplateResponse(base_template, ctx)
    

    
from sqlalchemy import and_, or_, Date, DateTime, Boolean, String, Integer
from sqlalchemy.inspection import inspect

from sqlalchemy import or_, and_, inspect, Boolean, Integer, String, Date, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.types import JSON as SQLAlchemyJSON

from sqlalchemy import or_, and_, inspect, Boolean, Integer, String, Date, DateTime

def build_filters(data: dict, model):


    """
    Build SQLAlchemy filters from form data.

    Features:
        - Booleans (direct column values)
        - Strings
        - Integers
        - Arrays
        - JSON / JSONB
        - Dates (with optional start/end ranges)
        - Filter types: exact, has, has-all, has-not, like
        - Extensive debug logging
    """
    filters = []
    mapper = inspect(model)
    column_types = {col.name: col.type for col in mapper.columns}

#    print("=== Starting build_filters ===")

    for field, value in data.items():
        if value in (None, "", []):
 #           print(f"Skipping empty field: {field}")
            continue

        col = getattr(model, field, None)
        if col is None:
  #          print(f"Skipping unknown column: {field}")
            continue

        col_type = column_types.get(field)
   #     print(f"\nProcessing field: {field}")
    #    print(f"  Column type: {col_type}")
     #   print(f"  Raw value: {value}")

        # Determine filter type for this field
        filter_type = data.get(f"{field}_type", "like")
#        print(f"  Filter type: {filter_type}")

        # BOOLEAN handling (direct column value)
        if isinstance(col_type, Boolean):
            # Convert string "true"/"false" to Python boolean
            if isinstance(value, str):
                val_str = value.lower()
                if val_str == "true":
                    val = True
                elif val_str == "false":
                    val = False
                else:
 #                   print(f"  Skipping invalid Boolean value for {field}: {value}")
                    continue
            else:
                val = bool(value)

            # If filtering for False, include NULL as False
            if val is False:
                f = or_(col == False, col.is_(None))
                print(f"  Adding Boolean filter (False or NULL): {field} = False/NULL")
            else:
                f = col == val
                print(f"  Adding Boolean filter: {field} = True")

            filters.append(f)
            continue

        # DATE / DATETIME
        if isinstance(col_type, (Date, DateTime)):
            print(f"  Handling date/datetime")
            if isinstance(value, dict):
                if "start" in value:
                    f = col >= value["start"]
                    print(f"  Adding start date filter: {f}")
                    filters.append(f)
                if "end" in value:
                    f = col <= value["end"]
                    print(f"  Adding end date filter: {f}")
                    filters.append(f)
            else:
                f = col == value
                print(f"  Adding exact date filter: {f}")
                filters.append(f)
            continue

        # INTEGER
        if isinstance(col_type, Integer):
            # Only process if the value is actually integer-like
            vals = value if isinstance(value, list) else [value]
            
            # Skip values that clearly aren’t numbers
            cleaned_vals = []
            for v in vals:
                if v in (None, "", []):
                    continue
                try:
                    cleaned_vals.append(int(v))
                except (ValueError, TypeError):
                    print(f"  Skipping non-integer value for {field}: {v}")
                    continue

            if not cleaned_vals:
                print(f"  No valid integers to filter for field: {field}")
                continue

            if filter_type == "exact":
                f = col == cleaned_vals[0] if len(cleaned_vals) == 1 else col.in_(cleaned_vals)
            elif filter_type in ("has", "has-all"):
                f = col.in_(cleaned_vals)
            elif filter_type == "has-not":
                f = ~col.in_(cleaned_vals)
            else:
                print(f"  Unknown integer filter type: {filter_type}")
                continue

            print(f"  Adding integer filter: {f}")
            filters.append(f)
            continue

        # STRING
        if isinstance(col_type, String):
            vals = value if isinstance(value, list) else [value]
            vals = [str(v) for v in vals if v not in (None, "")]
            if not vals:
                print(f"  Skipping string field (empty after cleaning): {field}")
                continue

            if filter_type == "exact":
                f = or_(*[col == v for v in vals])
            elif filter_type == "has":
                f = or_(*[col.contains(v) for v in vals])
            elif filter_type == "has-all":
                f = and_(*[col.contains(v) for v in vals])
            elif filter_type == "has-not":
                f = and_(*[~col.contains(v) for v in vals])
            elif filter_type == "like":
                f = col.ilike(f"%{vals[0]}%")
            else:
                print(f"  Unknown string filter type: {filter_type}")
                continue

            print(f"  Adding string filter: {f}")
            filters.append(f)
            continue

        # ARRAY
        if isinstance(col_type, ARRAY):
            vals = value if isinstance(value, list) else [value]
            vals = [v for v in vals if v not in (None, "", [])]
            if not vals:
                print(f"  Skipping array field (empty after cleaning): {field}")
                continue

            if filter_type == "has":
                f = or_(*[col.any(v) for v in vals])
            elif filter_type == "has-all":
                f = and_(*[col.any(v) for v in vals])
            elif filter_type == "has-not":
                f = and_(*[~col.any(v) for v in vals])
            elif filter_type == "exact":
                f = col == vals
            else:
                print(f"  Unknown array filter type: {filter_type}")
                continue

            print(f"  Adding array filter: {f}")
            filters.append(f)
            continue

        # JSON / JSONB / CSV / single value
        if isinstance(col_type, (JSON, JSONB, String)):
            # Normalize input into a list of search values
            if isinstance(value, list):
                vals = [v for v in value if v not in (None, "", [])]
            elif isinstance(value, str):
                # Split CSV string into individual search terms, strip spaces
                vals = [v.strip().strip("'\"") for v in value.split(",") if v.strip()]
            else:
                vals = [value]

            if not vals:
                continue

            conditions = []

            for v in vals:
                # Clean value to match CSV in SQLite (remove surrounding quotes)
                v_clean = v.strip("'\"")

                # CSV matching (handles optional spaces and quotes)
                csv_cond = or_(
                    col.like(f'"{v_clean},%'),    # start
                    col.like(f'{v_clean},%'),    # start
                    col.like(f'{v_clean}, %'),   # start with space
                    col.like(f'%,{v_clean},%'),  # middle
                    col.like(f'%, {v_clean},%'), # middle with space
                    col.like(f'%,{v_clean}"'),    # end
                    col.like(f'%, {v_clean}')    # end with space
                )

                # JSON array stored as text (SQLite-safe)
                if isinstance(col_type, (JSON, JSONB)):
                    json_cond = col.like(f'%"{v_clean}"%')
                    cond = or_(csv_cond, json_cond)
                else:
                    cond = csv_cond

                conditions.append(cond)

            # Combine conditions based on filter_type
            if filter_type == "has":
                f = or_(*conditions)
            elif filter_type == "has-all":
                f = and_(*conditions)
            elif filter_type == "has-not":
                f = and_(*[~c for c in conditions])
            elif filter_type == "exact":
                # Python-side order-independent exact match
                f = {"exact_vals": vals, "column": col.key}
            else:
                continue

            filters.append(f)
            print(f"  Adding JSON/CSV filter: {f}")
            continue
        # Only print skipped if no handler matched
        print(f"  Skipped field (no matching type handler): {field}")


#    print("=== Finished build_filters ===")
#    print(f"Total filters added: {len(filters)}")
    return filters


import re

def formatPhoneNr(number: str, country_code: str = '+46') -> str:
    """
    Normalize and format a phone number into international format.

    - Keeps only digits and '+'.
    - Converts '00' prefix to '+'.
    - If missing '+', adds country_code and removes one leading 0 from the local part.
    - Does not remove leading 0s from numbers that already start with '+'.
    """
    # Keep only digits and '+'
    number = re.sub(r'[^0-9+]', '', number)

    # Convert 00 -> +
    if number.startswith('00'):
        number = '+' + number[2:]

    # If no +, add country code and remove only the first leading 0 (if present)
    if not number.startswith('+'):
        if number.startswith('0'):
            number = country_code + number[1:]
        else:
            number = country_code + number

    # Do NOT remove any 0 if the number already had a + prefix.
    return number

from datetime import datetime, timezone

def local_to_utc(datetime_local_str: str, tz_name: str = constants.DEFAULT_TZ) -> datetime:
    """
    Convert a datetime-local string (YYYY-MM-DDTHH:MM) or date string (YYYY-MM-DD)
    from user's timezone to UTC-aware datetime.
    
    If only date is provided, assumes time 00:00.
    """
    try:
        if "T" in datetime_local_str:
            # datetime-local format
            naive_dt = datetime.strptime(datetime_local_str, "%Y-%m-%dT%H:%M")
        else:
            # date-only format, assume midnight
            naive_dt = datetime.strptime(datetime_local_str, "%Y-%m-%d")
        
        # Assign user timezone
        local_dt = naive_dt.replace(tzinfo=ZoneInfo(tz_name))
        # Convert to UTC
        utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
        return utc_dt
    except Exception as e:
        raise ValueError(f"Invalid datetime-local format: {datetime_local_str}") from e

def utc_to_local(dt, fmt: str = "%Y-%m-%d %H:%M", tz_name: str = constants.DEFAULT_TZ) -> str:
    """
    Convert a UTC datetime or UTC string to user's local timezone string.
    Parameters:
        dt: datetime or ISO8601 string in UTC
        tz_name: target timezone (default: Stockholm)
        fmt: output string format
    """

    if dt == None:
        return None

    # If input is a string, parse it as ISO format
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            # fallback: use current UTC time
            dt = datetime.now(tz=ZoneInfo("UTC"))

    # Ensure timezone-aware in UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    # Convert to target timezone
    local_dt = dt.astimezone(ZoneInfo(tz_name))
    return local_dt.strftime(fmt)