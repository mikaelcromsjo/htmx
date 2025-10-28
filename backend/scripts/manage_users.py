import sys, os

# Ensure /app/backend is in sys.path (works both inside and outside Docker)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

print("PYTHONPATH:", sys.path)  # <-- debug line

from getpass import getpass
from sqlalchemy.orm import Session
from models.models import Caller
from core.database import SessionLocal
from core.models.models import User
from passlib.context import CryptContext

# Example usage:
# docker exec -it fastapi_htmx_dev python /app/backend/scripts/manage_users.py admin_user --password Secret123 --admin 1 --caller "Main Office"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user(username: str, password: str, admin: int = 0, caller_name=None):
    db: Session = SessionLocal()
    try:
        # Handle caller creation or lookup
        caller = None
        if caller_name:
            caller = db.query(Caller).filter(Caller.name == caller_name).first()
            if not caller:
                caller = Caller(name=caller_name)
                db.add(caller)
                db.commit()
                db.refresh(caller)

        # Check if user already exists
        user = db.query(User).filter(User.username == username).first()
        hashed_password = pwd_context.hash(password)

        if user:
            # Update only allowed fields
            user.password_hash = hashed_password
            user.admin = admin
            user.caller = caller
            print(f"User '{username}' already exists — updated caller, password, and admin status ({admin}).")
        else:
            # Create new user
            user = User(
                username=username,
                password_hash=hashed_password,
                admin=admin,
                caller=caller
            )
            db.add(user)
            print(f"User '{username}' created successfully with admin={admin}.")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error creating or updating user: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage users in the system.")
    parser.add_argument("username", help="Username of the user to create or update")
    parser.add_argument("--password", help="Password for the user (prompted if omitted)")
    parser.add_argument("--admin", type=int, default=0, help="Admin level (0=normal user, 1=admin, etc.)")
    parser.add_argument("--caller", help="Caller name (optional)")

    args = parser.parse_args()

    password = args.password or getpass("Password: ")
    create_user(args.username, password, admin=args.admin, caller_name=args.caller)