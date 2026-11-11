from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.user import User


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), default="MEDIUM", nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("50.00"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="OPEN", nullable=False, index=True)
    resolved_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="fraud_alerts")
    resolver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by])

