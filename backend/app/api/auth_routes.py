
from fastapi import APIRouter, Depends, HTTPException, Request, status
import logging
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.rate_limit import auth_rate_limiter
from app.core.structured_logging import log_event
from app.database import get_db
from app.services.auth_service import (
    authenticate_customer,
    create_access_token,
)


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate a customer and issue a JWT access token."""

    client_ip = http_request.client.host if http_request.client else "unknown"
    auth_rate_limiter.check(f"ip:{client_ip}")

    customer = authenticate_customer(
        db=db,
        email=str(request.email),
        password=request.password,
    )

    if customer is None:
        # Use the same message for unknown emails and wrong passwords.
        log_event(logging.WARNING, "auth_failure", outcome="invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        access_token = create_access_token(customer.id)
    except RuntimeError as exc:
        # Do not expose configuration details to the client.
        log_event(
            logging.ERROR,
            "token_creation_failed",
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is temporarily unavailable.",
        ) from exc

    from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES

    return LoginResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=customer.role,
    )
