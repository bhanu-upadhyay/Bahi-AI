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
    from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
    from app.models.user import User


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    grn_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    received_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="RECEIVED", nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="goods_receipts")
    receiver: Mapped["User"] = relationship("User", back_populates="goods_receipts")
    lines: Mapped[List["GoodsReceiptLine"]] = relationship(
        "GoodsReceiptLine", back_populates="goods_receipt", cascade="all, delete-orphan"
    )


class GoodsReceiptLine(Base):
    __tablename__ = "goods_receipt_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    goods_receipt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("goods_receipts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purchase_order_line_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity_ordered: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity_accepted: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity_rejected: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    goods_receipt: Mapped["GoodsReceipt"] = relationship("GoodsReceipt", back_populates="lines")
    purchase_order_line: Mapped["PurchaseOrderLine"] = relationship(
        "PurchaseOrderLine", back_populates="goods_receipt_lines"
    )

