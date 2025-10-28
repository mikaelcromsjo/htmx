# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.models.base import Base
import os
from sqlalchemy.orm import relationship, Session
from core.models.models import BaseMixin, Update, User

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


def init_admin_user():
    db: Session = SessionLocal()

    admin = db.query(User).filter_by(username="admin").first()
    if not admin:
        admin = User(username="admin", admin=1)
        admin.set_password("1234")  # 🔒 use env var in prod
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print("✅ Default admin user created: admin / changeme")

    db.close()        
