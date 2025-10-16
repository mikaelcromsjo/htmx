from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
import os

from typing import Type
from typing import Any, Union

from pydantic import BaseModel

from templates import templates


def populate(update_dict: dict, db_obj: Any, pyd_model: Type[BaseModel]) -> Any:
    """
    Convert a raw dict (from Update) to a Pydantic model, then populate the DB model.
    Handles empty strings for int/bool/list/dict fields.
    """
    preprocessed = {}

    for field_name, value in update_dict.items():
        field_info = pyd_model.model_fields.get(field_name)
        if not field_info:
            continue

        field_type = field_info.annotation

        # Convert empty string to None for Optional[int] or Optional[float]
        if value == "" and (
            field_type == int
            or field_type == float
            or (getattr(field_type, '__origin__', None) is Union and type(None) in getattr(field_type, '__args__', []))
        ):
            preprocessed[field_name] = None
        else:
            preprocessed[field_name] = value

    # Now instantiate the Pydantic model (validation happens here)
    pyd_instance = pyd_model(**preprocessed)

    # Dynamically populate the DB model
    for field_name, value in pyd_instance.model_dump(exclude_unset=True).items():
        setattr(db_obj, field_name, convert_value_for_field(pyd_instance, field_name, value))

    return db_obj

def convert_value_for_field(pyd_instance: BaseModel, field_name: str, value: Any):
    """
    Convert value to correct type based on Pydantic field type.
    Handles int, bool, list, dict, Optional[...] automatically.
    """
    from typing import get_origin, get_args, Union
    field_type = pyd_instance.model_fields[field_name].annotation
    origin = get_origin(field_type)
    args = get_args(field_type)

    # Optional[T]
    if origin is Union and type(None) in args:
        non_none_type = next((a for a in args if a != type(None)), str)
        return _convert_value(non_none_type, value) if value not in ("", None) else None

    return _convert_value(field_type, value)


def _convert_value(field_type, value):
    from typing import get_origin
    import json

    origin = get_origin(field_type)

    if field_type == int:
        return int(value)
    if field_type == bool:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)
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
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON as SQLAlchemyJSON

from sqlalchemy import or_, and_, inspect, Boolean, Integer, String, Date, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.types import JSON as SQLAlchemyJSON

from sqlalchemy import or_, and_, inspect, Boolean, Integer, String, Date, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.types import JSON as SQLAlchemyJSON

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

    print("=== Starting build_filters ===")

    for field, value in data.items():
        if value in (None, "", []):
            print(f"Skipping empty field: {field}")
            continue

        col = getattr(model, field, None)
        if col is None:
            print(f"Skipping unknown column: {field}")
            continue

        col_type = column_types.get(field)
        print(f"\nProcessing field: {field}")
        print(f"  Column type: {col_type}")
        print(f"  Raw value: {value}")

        # Determine filter type for this field
        filter_type = data.get(f"{field}_type", "like")
        print(f"  Filter type: {filter_type}")

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
                    print(f"  Skipping invalid Boolean value for {field}: {value}")
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

        # JSON / JSONB
        if isinstance(col_type, (SQLAlchemyJSON, JSONB)):
            vals = value if isinstance(value, list) else [value]
            vals = [v for v in vals if v not in (None, "", [])]
            if not vals:
                print(f"  Skipping JSON field (empty after cleaning): {field}")
                continue

            if filter_type == "has":
                f = or_(*[col.contains([v]) for v in vals])
            elif filter_type == "has-all":
                f = col.contains(vals)
            elif filter_type == "has-not":
                f = and_(*[~col.contains([v]) for v in vals])
            elif filter_type == "exact":
                f = col == vals
            else:
                print(f"  Unknown JSON filter type: {filter_type}")
                continue

            print(f"  Adding JSON filter: {f}")
            filters.append(f)
            continue

        print(f"  Skipped field (no matching type handler): {field}")

    print("=== Finished build_filters ===")
    print(f"Total filters added: {len(filters)}")
    return filters
