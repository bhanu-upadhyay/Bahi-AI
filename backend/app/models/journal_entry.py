from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Boolean,
    Date,
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
    from app.models.chart_of_account import ChartOfAccount
    from app.models.department import Department
    from app.models.invoice import Invoice
    from app.models.user import User
    from app.models.vendor import Vendor
    from app.models.erp_posting import ERPPosting


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entry_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    invoice_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    posting_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    accounting_period: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # e.g., "2026-11"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    total_debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    total_credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    is_balanced: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="POSTED", nullable=False, index=True
    )  # POSTED, REVERSED, DRAFT
    reversal_of_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    invoice: Mapped[Optional["Invoice"]] = relationship("Invoice", back_populates="journal_entries")
    lines: Mapped[List["JournalEntryLine"]] = relationship(
        "JournalEntryLine",
        back_populates="journal_entry",
        cascade="all, delete-orphan",
        order_by="JournalEntryLine.line_number",
    )
    reversal_entry: Mapped[Optional["JournalEntry"]] = relationship(
        "JournalEntry", remote_side=[id], foreign_keys=[reversal_of_id]
    )
    creator: Mapped[Optional["User"]] = relationship("User")
    erp_postings: Mapped[List["ERPPosting"]] = relationship("ERPPosting", back_populates="journal_entry")


class JournalEntryLine(Base):
    __tablename__ = "journal_entry_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    journal_entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vendor_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    journal_entry: Mapped["JournalEntry"] = relationship("JournalEntry", back_populates="lines")
    account: Mapped["ChartOfAccount"] = relationship("ChartOfAccount", back_populates="journal_lines")
    department: Mapped[Optional["Department"]] = relationship("Department")
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor")
