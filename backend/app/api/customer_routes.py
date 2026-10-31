
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_customer
from app.database import get_db
from app.models import Customer
from app.schemas.customer import (
    AdminCustomerResponse,
    CustomerActiveUpdate,
    CustomerCreate,
    CustomerResponse,
)
from app.core.security import require_admin
from app.core.rate_limit import auth_rate_limiter


router = APIRouter(
    prefix="/api/customers",
    tags=["Customers"],
)

password_hasher = PasswordHash.recommended()


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    customer_data: CustomerCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Register a customer without storing their plain-text password."""

    client_ip = request.client.host if request.client else "unknown"
    auth_rate_limiter.check(f"ip:{client_ip}")

    existing = db.scalar(
        select(Customer).where(
            Customer.email == str(customer_data.email)
        )
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with this email already exists",
        )

    customer = Customer(
        name=customer_data.name,
        email=str(customer_data.email),
        password_hash=password_hasher.hash(
            customer_data.password
        ),
    )

    try:
        db.add(customer)
        db.commit()
        db.refresh(customer)
    except IntegrityError:
        # Protect against duplicate registrations arriving concurrently.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with this email already exists",
        )

    return customer


@router.get(
    "/admin/all",
    response_model=list[AdminCustomerResponse],
)
def list_customers(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin_customer: Customer = Depends(require_admin),
):
    return db.scalars(
        select(Customer)
        .order_by(Customer.id)
        .offset(offset)
        .limit(limit)
    ).all()


@router.get(
    "/admin/{customer_id}",
    response_model=AdminCustomerResponse,
)
def get_admin_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    admin_customer: Customer = Depends(require_admin),
):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.patch(
    "/admin/{customer_id}/active",
    response_model=AdminCustomerResponse,
)
def update_customer_active(
    customer_id: int,
    active_data: CustomerActiveUpdate,
    db: Session = Depends(get_db),
    admin_customer: Customer = Depends(require_admin),
):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    if customer.id == admin_customer.id and not active_data.active:
        raise HTTPException(
            status_code=400, detail="Administrators cannot deactivate themselves."
        )
    customer.active = active_data.active
    db.commit()
    db.refresh(customer)
    return customer


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """Allow authenticated customers to retrieve only their own profile."""

    if customer_id != current_customer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access another customer's profile.",
        )

    customer = db.get(Customer, current_customer.id)

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    return customer
