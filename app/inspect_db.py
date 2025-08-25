from sqlalchemy import inspect
from app.database import engine

def list_tables():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print("📋 Tables in database:", tables)

if __name__ == "__main__":
    list_tables()