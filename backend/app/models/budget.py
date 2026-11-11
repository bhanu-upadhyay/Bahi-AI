from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.department import Department


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    fiscal_year: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    committed_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    spent_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    available_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("department_id", "fiscal_year", name="uq_dept_fiscal_year"),
        CheckConstraint("allocated_amount >= 0", name="chk_budget_allocated_nonnegative"),
        CheckConstraint("committed_amount >= 0", name="chk_budget_committed_nonnegative"),
        CheckConstraint("spent_amount >= 0", name="chk_budget_spent_nonnegative"),
    )

    # Relationships
    department: Mapped["Department"] = relationship("Department", back_populates="budgets")

