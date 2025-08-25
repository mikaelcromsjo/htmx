# app/templates.py
from fastapi.templating import Jinja2Templates
import os

# Point to your templates directory
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
