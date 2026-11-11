from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.purchase_order import PurchaseOrder
    from app.models.invoice import Invoice


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vendor_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    contact_person: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    tax_identifier: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    bank_account_last_four: Mapped[str] = mapped_column(String(4), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship("PurchaseOrder", back_populates="vendor")
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="vendor")

