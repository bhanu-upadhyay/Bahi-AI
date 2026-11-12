from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.journal_entry import JournalEntry
    from app.models.user import User


class ERPPosting(Base):
    __tablename__ = "erp_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("invoices.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    journal_entry_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("journal_entries.id", ondelete="SET NULL"), index=True, nullable=True
    )
    erp_adapter: Mapped[str] = mapped_column(
        String(50), default="MOCK_UNIVERSITY_ERP", nullable=False, index=True
    )
    erp_document_reference: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default="SYNCED", nullable=False, index=True
    )  # PENDING, QUEUED, SYNCING, SYNCED, FAILED, RETRY_PENDING
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    request_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    response_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="erp_posting")
    journal_entry: Mapped[Optional["JournalEntry"]] = relationship("JournalEntry", back_populates="erp_postings")
    poster: Mapped[Optional["User"]] = relationship("User")
    sync_logs: Mapped[List["ERPSyncLog"]] = relationship(
        "ERPSyncLog", back_populates="erp_posting", cascade="all, delete-orphan", order_by="ERPSyncLog.created_at.desc()"
    )


class ERPSyncLog(Base):
    __tablename__ = "erp_sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    erp_posting_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("erp_postings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    invoice_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # POST, RETRY, STATUS_CHECK, REVERSE
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # SUCCESS, FAILED, IN_PROGRESS
    request_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    response_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    erp_posting: Mapped[Optional["ERPPosting"]] = relationship("ERPPosting", back_populates="sync_logs")
    invoice: Mapped[Optional["Invoice"]] = relationship("Invoice")
