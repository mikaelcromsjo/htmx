import sys
import os
import argparse
import json
from sqlalchemy.orm import Session
from sqlalchemy import inspect

# --- Path setup ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.database import SessionLocal
from models.models import Caller, Customer, Call, Product, ProductCustomer
from core.models.models import User

# Map class names to actual classes
MODEL_MAP = {
    "Caller": Caller,
    "Customer": Customer,
    "Call": Call,
    "Product": Product,
    "ProductCustomer": ProductCustomer,
    "User": User
}

def print_schema(cls):
    print(f"Schema for {cls.__name__}:")
    mapper = inspect(cls)
    for col in mapper.columns:
        print(f"  {col.name} ({col.type})")
    print("-" * 40)

def print_rows(session: Session, cls, limit=None, filter_str=None):
    query = session.query(cls)
    if filter_str:
        query = query.filter(eval(filter_str))
    if limit:
        query = query.limit(limit)
    rows = query.all()

    for row in rows:
        row_dict = {}
        for col in inspect(cls).columns:
            val = getattr(row, col.name)
            if isinstance(val, (dict, list)):
                val = json.dumps(val)
            row_dict[col.name] = val
        print(row_dict)

def main():
    parser = argparse.ArgumentParser(description="Inspect database table")
    parser.add_argument("--database", type=str, required=True,
                        help="Model class name to inspect, e.g., Customer")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit the number of rows displayed")
    parser.add_argument("--filter", type=str, default=None,
                        help="SQLAlchemy filter string, e.g., 'Customer.user_id==1'")
    args = parser.parse_args()

    cls = MODEL_MAP.get(args.database)
    if not cls:
        print(f"Error: Unknown model {args.database}. Choose from: {', '.join(MODEL_MAP.keys())}")
        return

    session = SessionLocal()
    try:
        print_schema(cls)
        print_rows(session, cls, limit=args.limit, filter_str=args.filter)
    finally:
        session.close()


if __name__ == "__main__":
    main()
