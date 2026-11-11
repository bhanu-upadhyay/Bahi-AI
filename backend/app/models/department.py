from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.budget import Budget
    from app.models.purchase_order import PurchaseOrder
    from app.models.invoice import Invoice


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="department")
    budgets: Mapped[List["Budget"]] = relationship("Budget", back_populates="department")
    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship(
        "PurchaseOrder", back_populates="department"
    )
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="department")

