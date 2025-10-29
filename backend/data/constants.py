import json
from pathlib import Path

DATA_DIR = Path("./data")

def load_json(filename):
    path = DATA_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# --- Load data ---
categories = load_json("categories.json")
organisations = load_json("organisations.json")
personalities = load_json("personalities.json")

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

organisations_map = {org["id"]: org["name"] for org in organisations}
personalities_map = {p["id"]: p for p in personalities}