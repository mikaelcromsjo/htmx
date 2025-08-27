# app/templates.py
from fastapi.templating import Jinja2Templates
import os

# Point to your templates directory

templates = Jinja2Templates("app/templates")