from datetime import datetime, timezone
import logging
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog
from app.models.erp_posting import ERPPosting, ERPSyncLog
from app.models.invoice import Invoice
from app.services.erp.adapters import get_erp_adapter

logger = logging.getLogger("bahi_ai.erp.sync_service")


class SyncService:
    """Service responsible for ERP synchronization queue management,
    retry mechanisms, and sync audit trail.
    """

    def __init__(self):
        pass

    def get_sync_queue(self, db: Session) -> List[ERPPosting]:
        """Returns all postings currently queued, pending, or awaiting retry."""
        return (
            db.query(ERPPosting)
            .options(
                joinedload(ERPPosting.invoice),
                joinedload(ERPPosting.journal_entry),
            )
            .filter(ERPPosting.status.in_(["PENDING", "QUEUED", "FAILED", "RETRY_PENDING"]))
            .order_by(ERPPosting.updated_at.desc())
            .all()
        )

    def retry_failed_posting(
        self,
        posting_id: int,
        db: Session,
        user_id: Optional[int] = None,
    ) -> ERPPosting:
        """Safely retries a previously failed ERP posting."""
        logger.info(f"[SyncService] Retrying ERP posting ID {posting_id}")

        posting = (
            db.query(ERPPosting)
            .options(
                joinedload(ERPPosting.invoice),
                joinedload(ERPPosting.journal_entry),
            )
            .filter(ERPPosting.id == posting_id)
            .first()
        )
        if not posting:
            raise HTTPException(status_code=404, detail="ERP posting record not found")

        if posting.status == "SYNCED":
            return posting

        invoice = posting.invoice
        journal_entry = posting.journal_entry

        if not journal_entry:
            from app.services.erp.accounting_engine import AccountingEngine
            engine = AccountingEngine()
            journal_entry = engine.generate_journal_entry_for_invoice(invoice, db, user_id=user_id)
            posting.journal_entry_id = journal_entry.id

        # Invoke adapter with fresh retry
        adapter = get_erp_adapter(posting.erp_adapter)
        erp_res = adapter.post_invoice(
            journal_entry=journal_entry,
            invoice=invoice,
            idempotency_key=f"{posting.idempotency_key}-RETRY",
            simulate_failure=False,
        )

        posting.response_payload = erp_res

        if erp_res.get("success"):
            posting.status = "SYNCED"
            posting.erp_document_reference = erp_res["erp_document_reference"]
            posting.posted_at = datetime.now(timezone.utc)
            posting.error_message = None
            invoice.processing_status = "POSTED"

            # Log sync success
            sync_log = ERPSyncLog(
                erp_posting_id=posting.id,
                invoice_id=invoice.id,
                action="RETRY",
                status="SUCCESS",
                request_payload=posting.request_payload,
                response_payload=erp_res,
                duration_ms=erp_res.get("duration_ms", 20),
            )
            db.add(sync_log)

            audit = AuditLog(
                user_id=user_id,
                action="ERP_SYNC_RETRY_SUCCEEDED",
                entity_type="INVOICE",
                entity_id=str(invoice.id),
                new_values={
                    "posting_id": posting.id,
                    "erp_document_reference": posting.erp_document_reference,
                },
            )
            db.add(audit)
            db.commit()
            db.refresh(posting)
            return posting
        else:
            posting.status = "FAILED"
            posting.error_message = erp_res.get("error_message") or "Retry failed"

            sync_log = ERPSyncLog(
                erp_posting_id=posting.id,
                invoice_id=invoice.id,
                action="RETRY",
                status="FAILED",
                request_payload=posting.request_payload,
                response_payload=erp_res,
                error_details=posting.error_message,
                duration_ms=erp_res.get("duration_ms", 20),
            )
            db.add(sync_log)
            db.commit()
            db.refresh(posting)
            raise HTTPException(
                status_code=502,
                detail=f"Retry failed: {posting.error_message}",
            )

    def get_sync_history(self, db: Session, limit: int = 50) -> List[ERPSyncLog]:
        """Returns recent sync audit logs."""
        return (
            db.query(ERPSyncLog)
            .order_by(ERPSyncLog.created_at.desc())
            .limit(limit)
            .all()
        )
