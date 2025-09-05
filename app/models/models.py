from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker# Base class for models
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, JSON, Boolean
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import sqltypes as satypes
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from pydantic import BaseModel, field_validator

from app.database import Base
from typing import List, Optional
from typing import List, Optional, Dict, Any



# Py Models

class Update(BaseModel):
    class Config:
        extra = "allow"


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
                values[col.name] = []
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
                values[col.name] = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M")
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




# models set up in routes# ------------------------------------------------------
# SQLAlchemy Alarm model
# ------------------------------------------------------
class Alarm(BaseMixin, Base):
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    note = Column(String, nullable=True)


# -------------------------------------------------
# Customer Model (SQLAlchemy ORM)
# -------------------------------------------------
class Customer(BaseMixin, Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    code_name = Column(Integer, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    description_phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    contributes = Column(Integer, nullable=True) # 1 not, 2 contributes, 3 Silver, 4 Gold

    caller = Column(Integer, nullable=True) # key to caller database
    previous_caller = Column(JSON, default=[])
    previous_categories = Column(JSON, default=[])

    comment = Column(String, nullable=True)
    sub_caller = Column(String, nullable=True)
    organisations = Column(JSON, default=[])

    categories = Column(JSON, default=[])

    personality_type = Column(Integer, nullable=True) # 0 Unknown, 1 Yellow, 2 Blue, 3 Red, 4 Green,  

    controlled = Column(Boolean, default=False)

    likes_parties = Column(Boolean, default=False)
    likes_politics = Column(Boolean, default=False)
    likes_lectures = Column(Boolean, default=False)
    likes_activism = Column(Boolean, default=False)

    tags = Column(JSON, default=[])
    extra = Column(JSON, default={})

#

class CustomerUpdate(BaseModel):
    first_name: str
    last_name: str
    user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    comment: Optional[str] = None
    sub_caller: Optional[str] = None
    organisations: Optional[List[str]] = []      # Multi-select → list
    personality_type: Optional[int] = None       # Dropdown → int
    contributes: Optional[int] = None            # Dropdown → int
    caller: Optional[int] = None                 # Dropdown → int
    controlled: Optional[bool] = False           # Checkbox → bool
    likes_parties: Optional[bool] = False        # Checkbox → bool
    likes_politics: Optional[bool] = False
    likes_lectures: Optional[bool] = False
    likes_activism: Optional[bool] = False
    categories: Optional[List[str]] = []         # Multi-select → list
    tags: Optional[str] = ""                      # Comma-separated → list in populate()
    extra: Optional[str] = "{}"                   # JSON string → dict in populate()
    code_name: Optional[bool] = False            # Checkbox → bool    


# -----------------------------
# SQLAlchemy ORM Event model
# -----------------------------
class Event(BaseMixin, Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=True)
    description = Column(String, nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)

    type_parties = Column(Boolean, default=False)
    type_politics = Column(Boolean, default=False)
    type_lectures = Column(Boolean, default=False)
    type_activism = Column(Boolean, default=False)
    extra_external = Column(Boolean, default=False)
    extra_non_political = Column(Boolean, default=False)
    extra_visilble_all = Column(Boolean, default=False)

    extra = Column(JSON, nullable=True)

class EventUpdate(BaseModel):
    name: str
    price: Optional[int] = None
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None

    type_parties: bool = False
    type_politics: bool = False
    type_lectures: bool = False
    type_activism: bool = False
    extra_external: bool = False
    extra_non_political: bool = False
    extra_visilble_all: bool = False


#    extra: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True






#class Calls(BaseMixin, Base):
#    __tablename__ = "calls"
#
#    id = Column(Integer, primary_key=True, index=True)
#    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
#    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
#    status = Column(JSON, default=[])
#    note = Column(String, nullable=True)




        # -----------------------------
# SQLAlchemy ORM Event model
# -----------------------------
class Call(BaseMixin, Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    call_date = Column(DateTime, nullable=False)
    status = Column(JSON, default=[])
    note = Column(String, nullable=True)
    extra = Column(JSON, nullable=True)

class CallCreate(BaseModel):
    customer_id: int
    caller: int
    call_date: Optional[datetime] = None
    status: Optional[List[Any]] = []
    note: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class EventUpdate(BaseModel):
    name: str
    price: Optional[int] = None
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None

    type_parties: bool = False
    type_politics: bool = False
    type_lectures: bool = False
    type_activism: bool = False
    extra_external: bool = False
    extra_non_political: bool = False
    extra_visilble_all: bool = False


#    extra: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True