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

    # Get the search path from Jinja2 loader
    template_loader_paths = templates.env.loader.searchpath  # list of directories Jinja searches
    print("=== Template Debug ===")
    print("Jinja2 search paths:", template_loader_paths)
    for path in template_loader_paths:
        print("Full path to template:", os.path.join(path, template_name))
        print("Full path to base template:", os.path.join(path, base_template))
    print("=====================")

    if request.headers.get("hx-request"):
        return templates.TemplateResponse(template_name, context)
    else:
        ctx = context.copy()
        ctx["content_template"] = template_name
        return templates.TemplateResponse(base_template, ctx)