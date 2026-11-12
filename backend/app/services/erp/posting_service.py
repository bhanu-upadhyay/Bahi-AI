from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import logging
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.approval import Approval
from app.models.audit_log import AuditLog
from app.models.chart_of_account import ChartOfAccount
from app.models.erp_posting import ERPPosting, ERPSyncLog
from app.models.invoice import Invoice
from app.models.journal_entry import JournalEntry
from app.schemas.erp import (
    PostingEligibilityCheck,
    PostingEligibilityResponse,
)
from app.services.erp.accounting_engine import AccountingEngine
from app.services.erp.adapters import get_erp_adapter

logger = logging.getLogger("bahi_ai.erp.posting_service")


class PostingService:
    """Service responsible for ERP invoice posting eligibility verification,
    journal entry orchestration, adapter dispatch, and audit tracking.
    """

    def __init__(self):
        self.accounting_engine = AccountingEngine()

    def check_eligibility(self, invoice_id: int, db: Session) -> PostingEligibilityResponse:
        """Verifies if an invoice meets all strict criteria for ERP posting."""
        invoice = (
            db.query(Invoice)
            .options(
                joinedload(Invoice.vendor),
                joinedload(Invoice.department),
                joinedload(Invoice.approvals),
                joinedload(Invoice.erp_posting),
            )
            .filter(Invoice.id == invoice_id)
            .first()
        )
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        checks: List[PostingEligibilityCheck] = []
        blocking_reasons: List[str] = []
        warnings: List[str] = []

        # 1. Human Approval Check
        # Rule: Only an authorized human approval in approvals table may authorize posting.
        has_approved_status = invoice.approval_status == "APPROVED"
        has_approval_record = any(
            a.status == "APPROVED" for a in (invoice.approvals or [])
        )
        is_human_approved = has_approved_status or has_approval_record

        if is_human_approved:
            checks.append(
                PostingEligibilityCheck(
                    check_name="HUMAN_APPROVAL",
                    passed=True,
                    message="Invoice has been formally approved by authorized university officer.",
                )
            )
        else:
            checks.append(
                PostingEligibilityCheck(
                    check_name="HUMAN_APPROVAL",
                    passed=False,
                    message=f"Invoice approval status is '{invoice.approval_status}'. Human officer approval required before ERP posting.",
                )
            )
            blocking_reasons.append("Invoice is pending human approval sign-off.")

        # 2. Already Posted Check
        # Rule: Block posting if already synced to ERP
        already_posted = False
        if invoice.erp_posting and invoice.erp_posting.status == "SYNCED":
            already_posted = True
            checks.append(
                PostingEligibilityCheck(
                    check_name="POSTING_STATUS",
                    passed=False,
                    message=f"Invoice has already been posted to ERP (Ref: {invoice.erp_posting.erp_document_reference}).",
                )
            )
            blocking_reasons.append(
                f"Already posted to ERP under document #{invoice.erp_posting.erp_document_reference}."
            )
        else:
            checks.append(
                PostingEligibilityCheck(
                    check_name="POSTING_STATUS",
                    passed=True,
                    message="Invoice has not been posted to ERP.",
                )
            )

        # 3. Processing and Exception Status
        if invoice.processing_status in ["DUPLICATE", "FAILED"]:
            checks.append(
                PostingEligibilityCheck(
                    check_name="PROCESSING_STATUS",
                    passed=False,
                    message=f"Invoice is flagged with invalid processing status: {invoice.processing_status}.",
                )
            )
            blocking_reasons.append(f"Invoice marked as {invoice.processing_status}.")
        else:
            checks.append(
                PostingEligibilityCheck(
                    check_name="PROCESSING_STATUS",
                    passed=True,
                    message=f"Invoice processing status ({invoice.processing_status}) is valid for posting.",
                )
            )

        # 4. Financial Consistency
        total_amt = Decimal(str(invoice.total_amount or "0.00"))
        if total_amt <= Decimal("0.00"):
            checks.append(
                PostingEligibilityCheck(
                    check_name="FINANCIAL_RECONCILIATION",
                    passed=False,
                    message="Invoice total amount is zero or negative.",
                )
            )
            blocking_reasons.append("Invoice grand total must be positive.")
        else:
            checks.append(
                PostingEligibilityCheck(
                    check_name="FINANCIAL_RECONCILIATION",
                    passed=True,
                    message=f"Total amount ({invoice.currency} {total_amt}) is valid.",
                )
            )

        # 5. Vendor Registration
        if not invoice.vendor_id or not invoice.vendor:
            checks.append(
                PostingEligibilityCheck(
                    check_name="VENDOR_VERIFICATION",
                    passed=False,
                    message="Invoice is not linked to a registered vendor in university master directory.",
                )
            )
            blocking_reasons.append("Vendor must be registered before ERP ledger voucher generation.")
        elif not invoice.vendor.is_active:
            checks.append(
                PostingEligibilityCheck(
                    check_name="VENDOR_VERIFICATION",
                    passed=False,
                    message=f"Vendor '{invoice.vendor.legal_name}' is inactive.",
                )
            )
            blocking_reasons.append("Vendor account is disabled in vendor master.")
        else:
            checks.append(
                PostingEligibilityCheck(
                    check_name="VENDOR_VERIFICATION",
                    passed=True,
                    message=f"Vendor '{invoice.vendor.legal_name}' ({invoice.vendor.vendor_code}) is active.",
                )
            )

        # 6. Department Assignment
        if not invoice.department_id:
            checks.append(
                PostingEligibilityCheck(
                    check_name="DEPARTMENT_ENCUMBRANCE",
                    passed=False,
                    message="Department cost center not assigned.",
                    severity="WARNING",
                )
            )
            warnings.append("Department not specified; defaulting to central administration cost center.")
        else:
            checks.append(
                PostingEligibilityCheck(
                    check_name="DEPARTMENT_ENCUMBRANCE",
                    passed=True,
                    message=f"Department cost center {invoice.department.code if invoice.department else ''} assigned.",
                )
            )

        # 7. Chart of Accounts Check
        accounts_count = db.query(ChartOfAccount).filter(ChartOfAccount.is_active.is_(True)).count()
        if accounts_count < 4:
            checks.append(
                PostingEligibilityCheck(
                    check_name="ACCOUNT_MAPPINGS",
                    passed=False,
                    message="Chart of Accounts is incomplete in database.",
                )
            )
            blocking_reasons.append("University Chart of Accounts must be configured.")
        else:
            checks.append(
                PostingEligibilityCheck(
                    check_name="ACCOUNT_MAPPINGS",
                    passed=True,
                    message=f"Chart of Accounts active with {accounts_count} GL accounts.",
                )
            )

        is_eligible = len(blocking_reasons) == 0

        return PostingEligibilityResponse(
            invoice_id=invoice.id,
            eligible=is_eligible,
            human_approved=is_human_approved,
            already_posted=already_posted,
            checks=checks,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
        )

    def post_invoice_to_erp(
        self,
        invoice_id: int,
        db: Session,
        user_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        simulate_failure: bool = False,
        comments: Optional[str] = None,
    ) -> ERPPosting:
        """Executes full ERP posting workflow for an approved invoice."""
        logger.info(f"[PostingService] Starting ERP posting workflow for Invoice ID {invoice_id}")

        invoice = (
            db.query(Invoice)
            .options(
                joinedload(Invoice.vendor),
                joinedload(Invoice.department),
                joinedload(Invoice.lines),
                joinedload(Invoice.approvals),
                joinedload(Invoice.erp_posting),
            )
            .filter(Invoice.id == invoice_id)
            .first()
        )
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # 1. Idempotency Check
        if idempotency_key:
            existing_posting = (
                db.query(ERPPosting).filter(ERPPosting.idempotency_key == idempotency_key).first()
            )
            if existing_posting and existing_posting.status == "SYNCED":
                logger.info(f"[PostingService] Idempotency match: returning existing ERP posting #{existing_posting.id}")
                return existing_posting

        # 2. Eligibility Enforcement
        eligibility = self.check_eligibility(invoice_id, db)
        if not eligibility.eligible:
            reasons_str = "; ".join(eligibility.blocking_reasons)
            logger.error(f"[PostingService] Invoice #{invoice_id} rejected for posting: {reasons_str}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invoice is not eligible for ERP posting: {reasons_str}",
            )

        # 3. Idempotency Key Determination if not provided
        if not idempotency_key:
            raw = f"INV-{invoice.id}-{invoice.invoice_number}-{invoice.total_amount}"
            idempotency_key = f"IDEMP-{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

        # Re-check existing posting by generated idempotency key
        existing_posting = (
            db.query(ERPPosting).filter(ERPPosting.idempotency_key == idempotency_key).first()
        )
        if existing_posting and existing_posting.status == "SYNCED":
            logger.info(f"[PostingService] Idempotency match: returning existing ERP posting #{existing_posting.id}")
            return existing_posting

        # 3. Double-Entry Journal Entry Generation
        journal_entry = self.accounting_engine.generate_journal_entry_for_invoice(
            invoice=invoice,
            db=db,
            user_id=user_id,
        )

        # 4. Dispatch to ERP Adapter
        adapter = get_erp_adapter("MOCK_UNIVERSITY_ERP")
        t0 = datetime.now(timezone.utc)
        erp_res = adapter.post_invoice(
            journal_entry=journal_entry,
            invoice=invoice,
            idempotency_key=idempotency_key,
            simulate_failure=simulate_failure,
        )

        # 5. Record ERP Posting Record
        posting = invoice.erp_posting
        if not posting:
            posting = ERPPosting(
                invoice_id=invoice.id,
                journal_entry_id=journal_entry.id,
                erp_adapter=adapter.adapter_name,
                erp_document_reference=erp_res.get("erp_document_reference") or f"MOCK-ERR-{invoice.id}",
                idempotency_key=idempotency_key,
                posted_by=user_id,
            )
            db.add(posting)
            db.flush()

        posting.journal_entry_id = journal_entry.id
        posting.request_payload = {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "total_amount": float(invoice.total_amount or 0),
            "journal_entry_number": journal_entry.entry_number,
            "comments": comments,
        }
        posting.response_payload = erp_res

        if erp_res.get("success"):
            posting.status = "SYNCED"
            posting.erp_document_reference = erp_res["erp_document_reference"]
            posting.posted_at = datetime.now(timezone.utc)
            posting.error_message = None
            invoice.processing_status = "POSTED"

            # Sync Log
            sync_log = ERPSyncLog(
                erp_posting_id=posting.id,
                invoice_id=invoice.id,
                action="POST",
                status="SUCCESS",
                request_payload=posting.request_payload,
                response_payload=erp_res,
                duration_ms=erp_res.get("duration_ms", 20),
            )
            db.add(sync_log)

            # Audit Log
            audit = AuditLog(
                user_id=user_id,
                action="ERP_INVOICE_POSTED",
                entity_type="INVOICE",
                entity_id=str(invoice.id),
                new_values={
                    "erp_document_reference": posting.erp_document_reference,
                    "journal_entry_number": journal_entry.entry_number,
                    "total_amount": float(invoice.total_amount or 0),
                    "adapter": adapter.adapter_name,
                },
            )
            db.add(audit)
            db.commit()
            db.refresh(posting)
            logger.info(
                f"[PostingService] Invoice #{invoice.invoice_number} successfully posted to ERP. "
                f"Ref: {posting.erp_document_reference}"
            )
            return posting
        else:
            posting.status = "FAILED"
            posting.error_message = erp_res.get("error_message") or "Unknown ERP communication error"

            # Sync Log
            sync_log = ERPSyncLog(
                erp_posting_id=posting.id,
                invoice_id=invoice.id,
                action="POST",
                status="FAILED",
                request_payload=posting.request_payload,
                response_payload=erp_res,
                error_details=posting.error_message,
                duration_ms=erp_res.get("duration_ms", 20),
            )
            db.add(sync_log)

            # Audit Log
            audit = AuditLog(
                user_id=user_id,
                action="ERP_POSTING_FAILED",
                entity_type="INVOICE",
                entity_id=str(invoice.id),
                new_values={
                    "error": posting.error_message,
                    "adapter": adapter.adapter_name,
                },
            )
            db.add(audit)
            db.commit()
            db.refresh(posting)
            logger.error(f"[PostingService] ERP posting failed for Invoice #{invoice.id}: {posting.error_message}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"ERP posting rejected by {adapter.adapter_name}: {posting.error_message}",
            )
