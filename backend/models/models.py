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
from sqlalchemy import Date
from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, field_validator
from core.functions.helpers import formatPhoneNr


# models set up in routes# ------------------------------------------------------
# SQLAlchemy Alarm model
# ------------------------------------------------------
class Alarm(BaseMixin, Base):
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer = relationship("Customer")
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    event = relationship("Event")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    note = Column(String, nullable=True)
    extra = Column(MutableDict.as_mutable(JSON), default=dict)



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
    filter_a = Column(Boolean, default=False)
    filter_b = Column(Boolean, default=False)
    filter_c = Column(Boolean, default=False)
    filter_d = Column(Boolean, default=False)
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
    filter_a: Optional[bool] = False             # Checkbox → bool
    filter_b: Optional[bool] = False
    filter_c: Optional[bool] = False
    filter_d: Optional[bool] = False
    categories: Optional[List[str]] = []         # Multi-select → list
    tags: Optional[str] = ""                     # Comma-separated → list in populate()
    extra: Optional[Dict[str, Any]] = None
    code_name: Optional[bool] = False            # Checkbox → bool

    # ✅ Auto-format phone number
    @field_validator("phone")
    def normalize_phone(cls, v: Optional[str]):
        if v:
            return formatPhoneNr(v)
        return v

# -------------------------------------------------
# Companies Model (SQLAlchemy ORM)
# -------------------------------------------------
class Company(BaseMixin, Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    caller_id = Column(Integer, ForeignKey("callers.id"), nullable=True)
    comment = Column(String, nullable=True)
    extra = Column(MutableDict.as_mutable(JSON), default=dict)


class CompanyUpdate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    comment: Optional[str] = None
    caller: Optional[int] = None                 # Dropdown → int
    extra: Optional[Dict[str, Any]] = None


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

    type_a = Column(Boolean, default=False)
    type_b = Column(Boolean, default=False)
    type_c = Column(Boolean, default=False)
    type_d = Column(Boolean, default=False)
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

    type_a: bool = False
    type_b: bool = False
    type_c: bool = False
    type_d: bool = False
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
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    # Relationship to customer
    company = relationship("Company")

    date = Column(DateTime, nullable=True)
    extra = Column(MutableDict.as_mutable(JSON), default=dict)    

class InvoiceUpdate(BaseModel):
    number: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None
    company_id: Optional[int] = None
    date: Optional[datetime] = None

    class Config:
        from_attributes = True # orm_mode




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
    note = Column(String, nullable=False)
    extra = Column(MutableDict.as_mutable(JSON), default=dict)    


class CallUpdate(BaseModel):
    id: Optional[str] = None
    customer_id: int
    call_date: Optional[datetime] = None
    status: int
    note: str = ""
    extra: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class EventUpdate(BaseModel):
    name: str
    price: Optional[int] = None
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None

    type_a: bool = False
    type_b: bool = False
    type_c: bool = False
    type_d: bool = False
    extra_external: bool = False
    extra_non_political: bool = False
    extra_visilble_all: bool = False


    extra: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

    

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