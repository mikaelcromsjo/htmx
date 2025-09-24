import sys
import os
from getpass import getpass
from argparse import ArgumentParser

# Add app package to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from core.database import SessionLocal
from models.models import User, Caller
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def set_user(username: str, password: str, admin: bool = False, caller_name: str | None = None):
    db: Session = SessionLocal()

    # Handle caller
    caller = None
    if caller_name:
        caller = db.query(Caller).filter_by(name=caller_name).first()
        if not caller:
            caller = Caller(name=caller_name)
            db.add(caller)
            db.commit()
            db.refresh(caller)

    # Handle user
    user = db.query(User).filter_by(username=username).first()
    if user:
        user.password_hash = pwd_context.hash(password)
        user.admin = 1 if admin else 0
        if caller:
            user.caller_id = caller.id
        print(f"Updated user: {username}")
    else:
        user = User(
            username=username,
            password_hash=pwd_context.hash(password),
            admin=1 if admin else 0,
            caller_id=caller.id if caller else None
        )
        db.add(user)
        print(f"Created user: {username}")

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        print(f"Error saving user: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = ArgumentParser(description="Manage users")
    parser.add_argument("username", help="Username")
    parser.add_argument("--password", help="Password (leave empty to prompt)")
    parser.add_argument("--admin", action="store_true", help="Make user admin")
    parser.add_argument("--caller", help="Caller name")
    args = parser.parse_args()

    password = args.password or getpass("Password: ")

    set_user(args.username, password, args.admin, args.caller)
