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


class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=True, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    execution_status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False, index=True)
    input_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_duration: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    invoice: Mapped[Optional["Invoice"]] = relationship("Invoice", back_populates="execution_logs")

