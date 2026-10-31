
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import get_current_customer, require_admin
from app.database import get_db
from app.models import Customer
from app.schemas.support_ticket import (
    SupportTicketAdminUpdate,
    SupportTicketCreate,
    SupportTicketDetailResponse,
    SupportTicketResponse,
    SupportTicketStatusUpdate,
    TicketReplyCreate,
)
from app.models import SupportTicket, TicketReply
from app.services.support_ticket_service import (
    create_support_ticket as create_ticket_service,
    list_customer_tickets,
    list_all_support_tickets,
    update_support_ticket_status,
)


router = APIRouter(
    prefix="/api/support-tickets",
    tags=["Support Tickets"],
)


@router.post(
    "",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_support_ticket(
    ticket_data: SupportTicketCreate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """Create a ticket for the authenticated customer."""

    try:
        return create_ticket_service(
            db=db,
            ticket_data=ticket_data,
            customer_id=current_customer.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/admin/all",
    response_model=list[SupportTicketResponse],
)
def get_all_support_tickets(
    ticket_status: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    admin_customer: Customer = Depends(require_admin),
):
    """List all customers' support tickets for administrators only."""

    statement = select(SupportTicket).order_by(SupportTicket.id.desc())
    if ticket_status:
        statement = statement.where(SupportTicket.status == ticket_status)
    if priority:
        statement = statement.where(SupportTicket.priority == priority)
    return db.scalars(statement.offset(offset).limit(limit)).all()


@router.patch(
    "/{ticket_id}/status",
    response_model=SupportTicketResponse,
)
def update_ticket_status(
    ticket_id: int,
    status_data: SupportTicketStatusUpdate,
    db: Session = Depends(get_db),
    admin_customer: Customer = Depends(require_admin),
):
    """Allow administrators to update a support ticket's status."""

    ticket = update_support_ticket_status(
        db=db,
        ticket_id=ticket_id,
        new_status=status_data.status,
    )

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found.",
        )

    return ticket


@router.get(
    "/{ticket_id}",
    response_model=SupportTicketDetailResponse,
)
def get_ticket_detail(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    statement = (
        select(SupportTicket)
        .options(selectinload(SupportTicket.replies))
        .where(SupportTicket.id == ticket_id)
    )
    if current_customer.role != "admin":
        statement = statement.where(
            SupportTicket.customer_id == current_customer.id
        )
    ticket = db.scalar(
        statement
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Support ticket not found.")
    return ticket


@router.patch(
    "/{ticket_id}",
    response_model=SupportTicketResponse,
)
def update_ticket(
    ticket_id: int,
    ticket_data: SupportTicketAdminUpdate,
    db: Session = Depends(get_db),
    admin_customer: Customer = Depends(require_admin),
):
    ticket = db.get(SupportTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Support ticket not found.")
    changes = ticket_data.model_dump(exclude_unset=True)
    if "assigned_admin_id" in changes:
        admin_id = changes["assigned_admin_id"]
        if admin_id is not None:
            assigned_admin = db.get(Customer, admin_id)
            if assigned_admin is None or assigned_admin.role != "admin":
                raise HTTPException(
                    status_code=422, detail="Assigned user must be an administrator."
                )
    for field, value in changes.items():
        setattr(ticket, field, value)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.post(
    "/{ticket_id}/replies",
    response_model=SupportTicketDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def reply_to_ticket(
    ticket_id: int,
    reply_data: TicketReplyCreate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    ticket = db.get(SupportTicket, ticket_id)
    if ticket is None or (
        current_customer.role != "admin"
        and ticket.customer_id != current_customer.id
    ):
        raise HTTPException(status_code=404, detail="Support ticket not found.")
    reply = TicketReply(
        ticket_id=ticket.id,
        author_id=current_customer.id,
        message=reply_data.message,
    )
    db.add(reply)
    db.commit()
    return db.scalar(
        select(SupportTicket)
        .options(selectinload(SupportTicket.replies))
        .where(SupportTicket.id == ticket_id)
    )


@router.get(
    "",
    response_model=list[SupportTicketResponse],
)
def get_customer_tickets(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """List tickets belonging only to the authenticated customer."""

    try:
        return list_customer_tickets(
            db=db,
            customer_id=current_customer.id,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
