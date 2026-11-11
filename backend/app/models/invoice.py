from datetime import date, datetime
from decimal import Decimal
import re
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.vendor import Vendor
    from app.models.purchase_order import PurchaseOrder
    from app.models.department import Department
    from app.models.approval import Approval
    from app.models.payment import Payment
    from app.models.fraud_alert import FraudAlert
    from app.models.agent_execution_log import AgentExecutionLog


def normalize_invoice_number(num: str) -> str:
    """Safely normalizes invoice number: uppercase alphanumeric characters only."""
    if not num:
        return ""
    return re.sub(r"[^A-Za-z0-9]", "", num).upper()


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    normalized_invoice_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    vendor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    purchase_order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    document_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status tracking
    extraction_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="RECEIVED", nullable=False, index=True)
    approval_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    payment_status: Mapped[str] = mapped_column(String(50), default="UNPAID", nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("vendor_id", "normalized_invoice_number", name="uq_vendor_normalized_invoice"),
        Index("ix_invoices_dept_status", "department_id", "processing_status"),
        Index("ix_invoices_approval_status", "approval_status"),
        Index("ix_invoices_payment_status", "payment_status"),
    )

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="invoices")
    purchase_order: Mapped[Optional["PurchaseOrder"]] = relationship("PurchaseOrder", back_populates="invoices")
    department: Mapped["Department"] = relationship("Department", back_populates="invoices")
    lines: Mapped[List["InvoiceLine"]] = relationship(
        "InvoiceLine", back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceLine.line_number"
    )
    approvals: Mapped[List["Approval"]] = relationship(
        "Approval", back_populates="invoice", cascade="all, delete-orphan", order_by="Approval.created_at"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="invoice", cascade="all, delete-orphan"
    )
    fraud_alerts: Mapped[List["FraudAlert"]] = relationship(
        "FraudAlert", back_populates="invoice", cascade="all, delete-orphan"
    )
    execution_logs: Mapped[List["AgentExecutionLog"]] = relationship(
        "AgentExecutionLog", back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="lines")

