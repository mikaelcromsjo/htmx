from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker# Base class for models
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from datetime import datetime


from app.database import Base

# models set up in routes# ------------------------------------------------------
# SQLAlchemy Alarm model
# ------------------------------------------------------
class Alarm(Base):
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, index=True)
    customerId = Column(Integer, ForeignKey("customers.id"), nullable=False)
    eventId = Column(Integer, ForeignKey("events.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    note = Column(String, nullable=True)

    # Relationships (optional)
    customer = relationship("Customer", back_populates="alarms")
    event = relationship("Event", back_populates="alarms")


# Extend Customer & Event models with reverse relations if not already present
# Customer.alarms = relationship("Alarm", back_populates="customer", cascade="all, delete-orphan")
# Event.alarms = relationship("Alarm", back_populates="event", cascade="all, delete-orphan")

# -------------------------------------------------
# Customer Model (SQLAlchemy ORM)
# -------------------------------------------------
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)

    # JSON fields
    caller = Column(JSON, default=[])
    comment = Column(String, nullable=True)
    personalityType = Column(JSON, default=[])
    sub_caller = Column(String, nullable=True)
    organisation = Column(String, nullable=True)
    categories = Column(JSON, default=[])
    tags = Column(JSON, default=[])
    alarms = relationship("Alarm", back_populates="customer")    
    extra = Column(JSON, default={})

    events = relationship("Event", back_populates="customer")


# -----------------------------
# SQLAlchemy ORM Event model
# -----------------------------
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    startDate = Column(DateTime, nullable=False)
    endDate = Column(DateTime, nullable=False)
    type = Column(String, nullable=True)
    alarms = relationship("Alarm", back_populates="event")    
    extra = Column(JSON, nullable=True)

    # ForeignKey to Customer
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="events")  # customer.events
    alarms = relationship("Alarm", back_populates="event")        # alarm.event