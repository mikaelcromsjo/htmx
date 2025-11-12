import sys, os, random, datetime
from sqlalchemy.orm import Session

# --- Path setup ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.database import SessionLocal
from models.models import Caller, Customer, Call, Event, EventCustomer
from core.models.models import User

# -----------------------------
# CONFIG (base numbers)
# -----------------------------
CUSTOMERS_PER_CALLER = 50
CALLS_PER_CUSTOMER = 200
EVENTS_COUNT = 10
EVENT_CUSTOMERS_PER_EVENT = 30
DATE_START = datetime.datetime(2026, 1, 1)
DATE_END = datetime.datetime(2026, 12, 31)

# -----------------------------
# HELPERS
# -----------------------------
def randomize(base, percent=0.2):
    """Return a value within ±percent of base"""
    delta = int(base * percent)
    return base + random.randint(-delta, delta)

def random_date(start, end):
    delta = end - start
    return start + datetime.timedelta(days=random.randint(0, delta.days))

# -----------------------------
# CREATE CALLERS AND USERS
# -----------------------------
def create_callers(session: Session, num_callers=5):
    callers, users = [], []
    for i in range(num_callers):
        caller = Caller(name=f"Caller {i+1}")
        session.add(caller)
        session.commit()  # ensure ID is set
        callers.append(caller)

        # Create test user for this caller
        user = User(username=f"user_{caller.id}", caller_id=caller.id, admin=0)
        user.set_password("password123")
        session.add(user)
        session.commit()
        users.append(user)

    print(f"Created {len(callers)} callers and {len(users)} users")
    return callers, users

# -----------------------------
# CREATE CUSTOMERS
# -----------------------------
def create_customers(session: Session, callers, users):
    customers = []
    for caller, user in zip(callers, users):
        num_customers = randomize(CUSTOMERS_PER_CALLER)
        for i in range(num_customers):
            cust = Customer(
                first_name=f"First{i}",
                last_name=f"Last{i}",
                caller_id=caller.id,
                user_id=user.id,
                email=f"user{i}@example.com"
            )
            session.add(cust)
            customers.append(cust)
    session.commit()
    print(f"Created {len(customers)} customers")
    return customers

# -----------------------------
# CREATE CALLS (realistic daily volume)
# -----------------------------
def create_calls(session: Session, customers):
    for cust in customers:
        num_calls = randomize(CALLS_PER_CUSTOMER)
        for _ in range(num_calls):
            # Pick a caller and simulate realistic daily calls
            call_date = random_date(DATE_START, DATE_END)
            status = random.choices([1,2,3], weights=[0.7,0.2,0.1])[0]  # more answered calls
            call = Call(
                customer_id=cust.id,
                caller_id=cust.caller_id,
                call_date=call_date,
                status=status,
                note="Test call"
            )
            session.add(call)
    session.commit()
    print("Calls created")

# -----------------------------
# CREATE EVENTS
# -----------------------------
def create_events(session: Session):
    events = []
    for i in range(EVENTS_COUNT):
        start_date = random_date(DATE_START, DATE_END)
        end_date = start_date + datetime.timedelta(days=random.randint(1,5))
        e = Event(
            name=f"Event {i+1}",
            start_date=start_date,
            end_date=end_date,
            type_a=random.choice([True, False]),
            type_b=random.choice([True, False]),
            type_c=random.choice([True, False]),
            type_d=random.choice([True, False])
        )
        session.add(e)
        events.append(e)
    session.commit()
    print(f"Created {len(events)} events")
    return events

# -----------------------------
# LINK CUSTOMERS TO EVENTS
# -----------------------------
def create_event_customers(session: Session, events, customers):
    for event in events:
        num_participants = randomize(EVENT_CUSTOMERS_PER_EVENT)
        sampled_customers = random.sample(customers, min(num_participants, len(customers)))
        for cust in sampled_customers:
            ec = EventCustomer(
                event_id=event.id,
                customer_id=cust.id,
                status=random.choices([1,2,3,4], weights=[0.1,0.3,0.3,0.3])[0]
            )
            session.add(ec)
    session.commit()
    print("Event customers linked")

# -----------------------------
# MAIN
# -----------------------------
def main():
    session = SessionLocal()
    try:
        callers, users = create_callers(session)
        customers = create_customers(session, callers, users)
        create_calls(session, customers)
        events = create_events(session)
        create_event_customers(session, events, customers)
        print("✅ Test data generation complete")
    finally:
        session.close()


if __name__ == "__main__":
    main()
