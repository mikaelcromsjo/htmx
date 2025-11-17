import json
from pathlib import Path
from zoneinfo import ZoneInfo  # Python 3.9+

DATA_DIR = Path("./data")

# put in admin #TODO
# 
DEFAULT_TZ = "Europe/Stockholm"
SHOW_PRODUCTS_X_DAYS = 5;

def load_json(filename):
    path = DATA_DIR / filename

    # If file does not exist → create it with empty JSON object
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        return {}

    # If the file exists → try loading it
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # If corrupted or unreadable → reset it
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        return {}


# --- Load data ---
categories = load_json("categories.json")
products = load_json("products.json")
organisations = load_json("organisations.json")
personalities = load_json("personalities.json")
filters = load_json("filters.json")

# --- Transform data ---
categories_map = {}
for cid, cat in categories.items():
    # Add category itself
    categories_map[cid] = {
        "name": cat["name"],
        "type": "category"
    }
    # Add items under this category
    for iid, item in cat["items"].items():
        categories_map[iid] = {
            "name": item,
            "parent": cid,
            "type": "item"
        }


# --- Transform data ---
products_map = {}
for pid, prod in products.items():
    products_map[pid] = {
        "name": prod["name"],
        "type": "product"
    }
    # Add items under this category
    for iid, item in prod["items"].items():
        products_map[iid] = {
            "name": item,
            "parent": pid,
            "type": "options"
        }


organisations_map = {org["id"]: org["name"] for org in organisations}
filters_map = {flt["id"]: flt["name"] for flt in filters}
personalities_map = {p["id"]: p for p in personalities}