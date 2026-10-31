"""One-time command for establishing Brightloop's first administrator."""

import argparse

from sqlalchemy import select

from .database import SessionLocal
from .models import User, UserRole
from .security import hash_password, validate_password_complexity


def create_initial_admin(email: str, full_name: str, password: str) -> None:
    email = email.lower()
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.role == UserRole.ADMIN)):
            raise SystemExit("An administrator already exists; use the protected staff endpoint instead.")
        db.add(User(email=email, full_name=full_name, password_hash=hash_password(password), role=UserRole.ADMIN))
        db.commit()
    print(f"Created administrator: {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Brightloop's first administrator.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    try:
        validate_password_complexity(args.password)
    except ValueError as error:
        raise SystemExit(str(error))
    create_initial_admin(args.email, args.name, args.password)
