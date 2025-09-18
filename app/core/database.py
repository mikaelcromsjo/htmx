# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.models.base import Base
import os


# SQLite URL (relative path, works inside Docker)
#DATABASE_URL = "sqlite:///./dbdata/app.db"
DATABASE_URL = os.environ["DATABASE_URL"]  # <- comes from docker-compose env


# Create engine
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session in FastAPI routes
def get_db():
    """
    Yields a SQLAlchemy session and ensures it is closed after use.
    Usage in routes:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
