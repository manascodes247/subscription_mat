"""Small, dependency-free authentication helpers for Brightloop.

Passwords are never stored directly. Tokens are signed, short-lived JWTs.
Set BRIGHTLOOP_SECRET_KEY to a long random value before production use.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserRole

PASSWORD_ITERATIONS = 600_000
SECRET_KEY = os.getenv("BRIGHTLOOP_SECRET_KEY", "development-only-change-me-before-production")
ALGORITHM = "HS256"
TOKEN_HOURS = int(os.getenv("BRIGHTLOOP_TOKEN_HOURS", "8"))
if os.getenv("BRIGHTLOOP_ENV", "development").lower() == "production" and len(SECRET_KEY) < 64:
    raise RuntimeError("BRIGHTLOOP_SECRET_KEY must contain at least 64 characters in production")
bearer_scheme = HTTPBearer(auto_error=False)


def validate_password_complexity(password: str) -> None:
    """Enforce the policy required for all newly set passwords."""
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    if not any(character.isupper() for character in password):
        raise ValueError("Password must include an uppercase letter")
    if not any(character.islower() for character in password):
        raise ValueError("Password must include a lowercase letter")
    if not any(not character.isalnum() for character in password):
        raise ValueError("Password must include a special character")


def create_one_time_token() -> str:
    return secrets.token_urlsafe(32)


def hash_one_time_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, iterations, salt_hex, digest_hex = stored_hash.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        ).hex()
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError):
        return False


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(user: User) -> str:
    header = _b64encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64encode(json.dumps({
        "sub": str(user.id), "role": user.role.value,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)).timestamp()),
    }, separators=(",", ":")).encode())
    signature = _b64encode(hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing access token")
    if not credentials:
        raise unauthorized
    try:
        header, payload, signature = credentials.credentials.split(".")
        expected = _b64encode(hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        claims = json.loads(_b64decode(payload))
        if int(claims["exp"]) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError
        user = db.get(User, int(claims["sub"]))
        if not user:
            raise ValueError
        return user
    except (ValueError, KeyError, json.JSONDecodeError):
        raise unauthorized


def require_roles(*roles: UserRole):
    def role_guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission for this action")
        return current_user
    return role_guard
