
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer
from app.services.auth_service import decode_access_token


bearer_scheme = HTTPBearer()


def get_current_customer(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> Customer:
    """
    Identify the customer from a valid bearer token.

    The customer ID is extracted from the signed token, not from
    a request body or an LLM-generated tool argument.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        customer_id = decode_access_token(credentials.credentials)
    except RuntimeError:
        # Authentication configuration is missing or invalid.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is temporarily unavailable.",
        )

    if customer_id is None:
        raise credentials_exception

    customer = db.get(Customer, customer_id)

    if customer is None:
        raise credentials_exception

    return customer


def require_admin(
    current_customer: Annotated[
        Customer,
        Depends(get_current_customer),
    ],
) -> Customer:
    """Allow access only to customers with the admin role."""

    if current_customer.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )

    return current_customer
