from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.approval import Approval
    from app.models.goods_receipt import GoodsReceipt
    from app.models.audit_log import AuditLog


class UserRole(str, Enum):
    VENDOR = "VENDOR"
    HOD = "HOD"
    PROCUREMENT_OFFICER = "PROCUREMENT_OFFICER"
    FINANCE_OFFICER = "FINANCE_OFFICER"
    FINANCE_ADMIN = "FINANCE_ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.FINANCE_OFFICER.value, nullable=False, index=True)
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="users")
    approvals: Mapped[List["Approval"]] = relationship("Approval", back_populates="approver")
    goods_receipts: Mapped[List["GoodsReceipt"]] = relationship("GoodsReceipt", back_populates="receiver")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")

