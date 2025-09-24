import sys, os
from getpass import getpass
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.models import Caller
from core.models.models import User
from passlib.context import CryptContext

# Add backend folder to sys.path so imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user(username: str, password: str, admin=False, caller_name=None):
    db: Session = SessionLocal()
    try:
        caller = None
        if caller_name:
            caller = db.query(Caller).filter(Caller.name == caller_name).first()
            if not caller:
                # create caller if it doesn't exist
                caller = Caller(name=caller_name)
                db.add(caller)
                db.commit()
                db.refresh(caller)

        hashed_password = pwd_context.hash(password)
        user = User(username=username, password_hash=hashed_password, admin=admin, caller=caller)
        db.add(user)
        db.commit()
        print(f"User '{username}' created successfully")
    except Exception as e:
        db.rollback()
        print(f"Error creating user: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("--password")
    parser.add_argument("--admin", action="store_true")
    parser.add_argument("--caller")
    args = parser.parse_args()

    password = args.password or getpass("Password: ")
    create_user(args.username, password, admin=args.admin, caller_name=args.caller)
