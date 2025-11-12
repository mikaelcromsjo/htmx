from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker# Base class for models
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, JSON, Boolean
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import sqltypes as satypes
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.mutable import MutableDict

from core.database import Base
from typing import Optional, Dict, Any

from passlib.context import CryptContext
from datetime import date, time

from typing import List

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# models set up customer routes# ------------------------------------------------------
# SQLAlchemy Calls model
# ------------------------------------------------------

# Optional: PG-specific types if you use Postgres
try:
    from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, JSONB as PG_JSONB
except Exception:
    PG_ARRAY = tuple()
    PG_JSONB = tuple()

class BaseMixin:
    """
    Mixin that provides .empty(**overrides) to construct an instance
    with 'empty' values inferred from column types.
    You can also define __empty_overrides__ = {...} on a model class.
    """
    __empty_overrides__ = {}


    def to_dict(self):
        return( {c.name: getattr(self, c.name) for c in self.__table__.columns})

    @classmethod
    def empty(cls, **overrides):
        values = {}
        for col in cls.__table__.columns:  # type: Column
            # Typically skip PKs; you can still provide one via overrides if you need it
            if col.primary_key:
                continue

            if col.name in overrides:
                values[col.name] = overrides[col.name]
                continue

            t = col.type

            # --- strings/text ---
            if isinstance(t, (satypes.String, satypes.Text, satypes.Unicode, satypes.UnicodeText)):
                values[col.name] = ""

            # --- JSON / arrays ---
            elif isinstance(t, (satypes.JSON,)) or (PG_JSONB and isinstance(t, PG_JSONB)):
                values[col.name] = {}
            elif (PG_ARRAY and isinstance(t, PG_ARRAY)) or isinstance(t, satypes.ARRAY):
                values[col.name] = []

            # --- booleans ---
            elif isinstance(t, satypes.Boolean):
                values[col.name] = False

            # --- integers / numerics ---
            elif isinstance(t, (satypes.Integer, satypes.SmallInteger, satypes.BigInteger)):
                values[col.name] = 0
            elif isinstance(t, (satypes.Numeric, satypes.Float, satypes.DECIMAL)):
                values[col.name] = 0

            # --- temporal ---
            elif isinstance(t, satypes.DateTime):
                values[col.name] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
            elif isinstance(t, satypes.Date):
                values[col.name] = date.today()
            elif isinstance(t, satypes.Time):
                values[col.name] = time(0, 0, 0)

            # --- fallback: use scalar Column default if present; else None ---
            else:
                if col.default is not None and getattr(col.default, "arg", None) is not None \
                   and not callable(getattr(col.default, "arg", None)):
                    values[col.name] = col.default.arg
                else:
                    values[col.name] = None

        # class-level defaults, then call-time overrides win
        values.update(getattr(cls, "__empty_overrides__", {}) or {})
        values.update(overrides)
        return cls(**values)
    

class User(BaseMixin, Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    admin = Column(Integer, default=0)  # 0 = normal user, 1 = admin
    caller_id = Column(Integer, ForeignKey("callers.id"), nullable=True)
    caller = relationship("Caller")
    extra = Column(MutableDict.as_mutable(JSON), default=dict)

    def verify_password(self, password: str):
        return pwd_context.verify(password, self.password_hash)

    def set_password(self, password: str):
        self.password_hash = pwd_context.hash(password)

class UserUpdate(BaseModel):
    caller_id: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

# Py Models

class Update(BaseModel):
    class Config:
        extra = "allow"



class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class TagLink(Base):
    __tablename__ = "tag_links"
    id = Column(Integer, primary_key=True)
    tag_id = Column(ForeignKey("tags.id"))
    object_id = Column(Integer, index=True)
    object_type = Column(String, index=True)  # e.g. "location", "product"

    tag = relationship("Tag")

