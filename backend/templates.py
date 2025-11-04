# app/templates.py
from fastapi.templating import Jinja2Templates
import os
from fastapi.templating import Jinja2Templates
from pathlib import Path
from jinja2 import ChoiceLoader, FileSystemLoader

# Point to your templates directory

# core templates path
core_templates_path = Path(__file__).parent / "core/templates"
# app-specific templates path
app_templates_path = Path(__file__).parent / "templates"

loader = ChoiceLoader([
    FileSystemLoader(str(app_templates_path)),
    FileSystemLoader(str(core_templates_path)),
])

# Jinja2 will look in this order
templates = Jinja2Templates(directory=str(app_templates_path))
templates.env.loader = loader

# 🔥 disable Jinja caching
templates.env.cache = {}
templates.env.auto_reload = True

