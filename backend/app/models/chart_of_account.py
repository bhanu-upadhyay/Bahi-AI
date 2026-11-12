from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.journal_entry import JournalEntryLine
    from app.models.account_mapping import AccountMapping


class ChartOfAccount(Base):
    __tablename__ = "chart_of_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    account_name: Mapped[str] = mapped_column(String(150), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    journal_lines: Mapped[List["JournalEntryLine"]] = relationship(
        "JournalEntryLine", back_populates="account"
    )
    debit_mappings: Mapped[List["AccountMapping"]] = relationship(
        "AccountMapping",
        foreign_keys="[AccountMapping.debit_account_id]",
        back_populates="debit_account",
    )
    credit_mappings: Mapped[List["AccountMapping"]] = relationship(
        "AccountMapping",
        foreign_keys="[AccountMapping.credit_account_id]",
        back_populates="credit_account",
    )
