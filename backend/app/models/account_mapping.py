from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Boolean,
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
    from app.models.chart_of_account import ChartOfAccount
    from app.models.department import Department
    from app.models.vendor import Vendor


class AccountMapping(Base):
    __tablename__ = "account_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mapping_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # DEFAULT_AP, DEFAULT_BANK, DEFAULT_TAX_CGST, DEFAULT_TAX_SGST, DEFAULT_TAX_IGST, DEPARTMENT, VENDOR, CATEGORY, ROUNDOFF
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    expense_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    debit_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    credit_account_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    debit_account: Mapped["ChartOfAccount"] = relationship(
        "ChartOfAccount", foreign_keys=[debit_account_id], back_populates="debit_mappings"
    )
    credit_account: Mapped[Optional["ChartOfAccount"]] = relationship(
        "ChartOfAccount", foreign_keys=[credit_account_id], back_populates="credit_mappings"
    )
