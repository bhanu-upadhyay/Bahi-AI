from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.user import User


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    approver_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    approval_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="approvals")
    approver: Mapped["User"] = relationship("User", back_populates="approvals")

