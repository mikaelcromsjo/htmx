from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker# Base class for models
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, JSON, Boolean
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import sqltypes as satypes
from datetime import datetime, timezone


from app.database import Base

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

class Calls(BaseMixin, Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(JSON, default=[])
    note = Column(String, nullable=True)


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

# -----------------------------
# SQLAlchemy ORM Event model
# -----------------------------
class Event(BaseMixin, Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    type = Column(JSON, default=[])
    extra = Column(JSON, nullable=True)
