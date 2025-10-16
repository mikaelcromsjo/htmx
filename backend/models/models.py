from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker# Base class for models
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, JSON, Boolean
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import sqltypes as satypes
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from pydantic import BaseModel, field_validator

from core.database import Base
from core.models.models import BaseMixin, Update

from typing import List, Optional, Dict, Any

from sqlalchemy.ext.mutable import MutableDict



# models set up in routes# ------------------------------------------------------
# SQLAlchemy Alarm model
# ------------------------------------------------------
class Alarm(BaseMixin, Base):
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    date = Column(DateTime, default=datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M"))
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
    code_name = Column(Boolean, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    description_phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    contributes = Column(Integer, nullable=True) # 1 not, 2 contributes, 3 Silver, 4 Gold

    caller_id = Column(Integer, ForeignKey("callers.id"), nullable=True)
    # Relationship to caller
    caller = relationship("Caller", back_populates="customers")
    
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
    extra = Column(MutableDict.as_mutable(JSON), default=dict)


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
    extra: Optional[Dict[str, Any]] = None
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

    extra = Column(MutableDict.as_mutable(JSON), default=dict)    

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


    extra: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True



# -----------------------------
# SQLAlchemy ORM Invoice model
# -----------------------------
class Invoice(BaseMixin, Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    # Relationship to customer
    customer = relationship("Customer")

    date = Column(DateTime, nullable=True)
    extra = Column(MutableDict.as_mutable(JSON), default=dict)    

class InvoiceUpdate(BaseModel):
    number: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None
    customer_id: Optional[int] = None

    class Config:
        orm_mode = True




# -----------------------------
# SQLAlchemy ORM Event model
# -----------------------------
class Call(BaseMixin, Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    caller_id = Column(Integer, ForeignKey("callers.id"), nullable=False)    
    call_date = Column(DateTime, nullable=False)
    status = Column(JSON, default=[])
    note = Column(String, nullable=True)
    extra = Column(MutableDict.as_mutable(JSON), default=dict)    


class CallUpdate(BaseModel):
    id: Optional[str] = None
    customer_id: int
    call_date: Optional[datetime] = None
    status: int
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


    extra: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True

    

class EventCustomer(BaseMixin, Base):
    __tablename__ = "event_customers"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(Integer, nullable=False)  # 0 = not going, 1 = going, 2 = interested


#

class Caller(BaseMixin, Base):
    __tablename__ = "callers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    # Backref to customers (one-to-many)
    customers = relationship("Customer", back_populates="caller")