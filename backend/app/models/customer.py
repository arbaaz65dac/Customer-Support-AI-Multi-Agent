
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # New customers are ordinary customers unless explicitly promoted
    # through a trusted administrative process.
    role: Mapped[str] = mapped_column(
        String(20),
        default="customer",
        server_default="customer",
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", index=True, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    # One customer can have multiple orders and support tickets.
    orders: Mapped[list["Order"]] = relationship(
        back_populates="customer",
    )

    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        back_populates="customer", foreign_keys="SupportTicket.customer_id"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    refund_requests: Mapped[list["RefundRequest"]] = relationship(
        back_populates="customer", foreign_keys="RefundRequest.customer_id"
    )
