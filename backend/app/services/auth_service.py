
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
)
from app.models import Customer


password_hasher = PasswordHash.recommended()


def authenticate_customer(
    db: Session,
    email: str,
    password: str,
) -> Customer | None:
    """Return the customer if the email and password are valid."""

    customer = db.scalar(
        select(Customer).where(Customer.email == email)
    )

    if customer is None:
        return None

    if not customer.active:
        return None

    if not password_hasher.verify(password, customer.password_hash):
        return None

    return customer


def create_access_token(customer_id: int) -> str:
    """Create a signed JWT access token for a verified customer."""

    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured."
        )

    if ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
        raise RuntimeError(
            "ACCESS_TOKEN_EXPIRE_MINUTES must be positive."
        )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(customer_id),
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> int | None:
    """Validate a JWT and return its customer ID, or None if invalid."""

    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured."
        )

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )

        subject = payload.get("sub")

        if not isinstance(subject, str):
            return None

        customer_id = int(subject)

        if customer_id <= 0:
            return None

        return customer_id

    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None
