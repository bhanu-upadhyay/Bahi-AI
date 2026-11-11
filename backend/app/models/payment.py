from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.invoice import Invoice


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_reference: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="SCHEDULED", nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(50), default="ACH", nullable=False)
    external_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="payments")

