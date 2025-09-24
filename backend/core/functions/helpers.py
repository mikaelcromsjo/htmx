from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
import os

from typing import Type
from typing import Any, Union

from pydantic import BaseModel

from app.templates import templates


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

def build_filters(data: dict, model):
    """
    Build SQLAlchemy filters from form data.
    Handles:
        - Scalar integers (caller, personality_type, contributes)
        - Booleans
        - Text fields
        - Multi-select / JSON / text array fields
        - Dates with start/end
        - Filter types: exact, has, has-all, has-not, like, true, false
    Prints exact SQLAlchemy filters.
    """
    filters = []
    mapper = inspect(model)
    column_types = {col.name: col.type for col in mapper.columns}


    for field, value in data.items():
        # Skip None or empty string
        if value in (None, ""):
            continue

        print("data", field, value)


        # BOOLEAN *_type
        if field.endswith("_type") and field[:-5] in column_types:
            print("bool")

            base_field = field[:-5]
            col = getattr(model, base_field)
            col_type = column_types.get(base_field)
            if isinstance(col_type, Boolean):
                val_str = str(value).lower()
                if val_str == "true":
                    f = col == True
                elif val_str == "false":
                    f = col == False
                else:
                    continue
                print(f"Adding filter: {f}")
                filters.append(f)
                continue

        # DATE ranges
        base_field = field
        is_start = False
        is_end = False
        if field.endswith("-start"):
            base_field = field[:-6]
            is_start = True
        elif field.endswith("-end"):
            base_field = field[:-4]
            is_end = True

        col = getattr(model, base_field, None)
        if not col:
            continue

        col_type = column_types.get(base_field)

       # 👇 Debug line here
        print(f"DEBUG field={base_field}, type={type(col_type)}, col_type={col_type}")

        filter_type = data.get(f"{field}_type", "like")

        # DATE
        if isinstance(col_type, (Date, DateTime)):
            print("date")
            if is_start:
                f = col >= value
            elif is_end:
                f = col <= value
            else:
                f = col == value
            print(f"Adding filter: {f}")
            filters.append(f)
            continue

        # INTEGER SCALAR (caller, personality_type, contributes)
        if isinstance(col_type, Integer):
            print("integer")
            vals = value if isinstance(value, list) else [value]
            # filter out empty strings / None
            vals = [v for v in vals if v not in (None, "", [])]
            if not vals:
                continue
            try:
                vals = [int(v) for v in vals]
            except ValueError:
                continue

            if filter_type in ("exact", "has"):
                if len(vals) == 1 and filter_type == "exact":
                    f = col == vals[0]
                else:
                    f = col.in_(vals)   # <- for 'has', use in_()
            elif filter_type == "has-not":
                f = ~col.in_(vals)

            print(f"Adding filter: {f}")
            filters.append(f)
            continue

        if isinstance(col_type, String):
            print ("string")
            vals = value if isinstance(value, list) else [value]
            # filter out empty / None
            vals = [str(v) for v in vals if v not in (None, "")]
            if not vals:
                continue

            if filter_type == "has":
                f = or_(*[col.contains(v) for v in vals])
            elif filter_type == "has-all":
                f = and_(*[col.contains(v) for v in vals])
            elif filter_type == "has-not":
                f = and_(*[~col.contains(v) for v in vals])
            elif filter_type == "exact":
                f = or_(*[col == v for v in vals])
            elif filter_type == "like":
                f = col.ilike(f"%{vals[0]}%")  # only first for single value

            if f is not None:
                print(f"Adding filter: field={field}, type={filter_type}, value={vals}, filter={f}")
                filters.append(f)

        if isinstance(col_type, ARRAY):
            print("array")
            vals = value if isinstance(value, list) else [value]
            vals = [v for v in vals if v not in (None, "", [])]
            if not vals:
                continue

            if filter_type == "has":
                # Matches if *any* element is present
                f = or_(*[col.any(v) for v in vals])
            elif filter_type == "has-all":
                # All must be present
                f = and_(*[col.any(v) for v in vals])
            elif filter_type == "has-not":
                f = and_(*[~col.any(v) for v in vals])
            elif filter_type == "exact":
                # Whole array equality
                f = col == vals
            else:
                continue

            print(f"Adding filter: field={field}, type={filter_type}, value={vals}, filter={f}")
            filters.append(f)
            continue

        # JSON / JSONB fields
        if isinstance(col_type, (SQLAlchemyJSON, JSONB)):
            print("json")
            vals = value if isinstance(value, list) else [value]
            vals = [v for v in vals if v not in (None, "", [])]
            if not vals:
                continue

            if filter_type == "has":
                # any value present
                f = or_(*[col.contains([v]) for v in vals])
            elif filter_type == "has-all":
                # must contain all
                f = col.contains(vals)
            elif filter_type == "has-not":
                f = and_(*[~col.contains([v]) for v in vals])
            elif filter_type == "exact":
                f = col == vals
            else:
                continue

            print(f"Adding filter: field={field}, type={filter_type}, value={vals}, filter={f}")
            filters.append(f)
            continue

                
    return filters
