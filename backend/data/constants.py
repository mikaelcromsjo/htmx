# Example categories dictionary (replace with your actual JSON source)
categories = {
    "c1": {"name": "Category1", "items": {
        "i1": "Item1",
        "i2": "Item2"
    }},
    "c2": {"name": "Category2", "items": {
        "i3": "ItemA",
        "i4": "ItemB"
    }},
}

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

organisations = [
    {"id": 1, "name": "Acme Corp"},
    {"id": 2, "name": "Globex Inc"},
    {"id": 3, "name": "Initech"},
    {"id": 4, "name": "Umbrella Corp"},
    {"id": 5, "name": "Hooli"}
]

organisations_map = {org["id"]: org["name"] for org in organisations}

personalities = [
    {"id": 0, "name": "Okänd"},
    {"id": 1, "name": "Gul"},
    {"id": 2, "name": "Blå"},
    {"id": 3, "name": "Röd"},
    {"id": 4, "name": "Grön"}]

personalities_map = {p["id"]: p for p in personalities}