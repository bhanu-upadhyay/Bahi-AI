from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
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
    from app.models.vendor import Vendor
    from app.models.department import Department
    from app.models.user import User
    from app.models.goods_receipt import GoodsReceipt, GoodsReceiptLine
    from app.models.invoice import Invoice


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    po_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    vendor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_delivery_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ISSUED", nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="purchase_orders")
    department: Mapped["Department"] = relationship("Department", back_populates="purchase_orders")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    lines: Mapped[List["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine", back_populates="purchase_order", cascade="all, delete-orphan", order_by="PurchaseOrderLine.line_number"
    )
    goods_receipts: Mapped[List["GoodsReceipt"]] = relationship(
        "GoodsReceipt", back_populates="purchase_order"
    )
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="purchase_order")


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    item_description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="lines")
    goods_receipt_lines: Mapped[List["GoodsReceiptLine"]] = relationship(
        "GoodsReceiptLine", back_populates="purchase_order_line"
    )

