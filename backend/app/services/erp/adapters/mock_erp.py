from datetime import datetime, timezone
import hashlib
import logging
import time
from typing import Any, Dict, Optional

from app.models.invoice import Invoice
from app.models.journal_entry import JournalEntry
from app.services.erp.adapters.base import ERPAdapterInterface

logger = logging.getLogger("bahi_ai.erp.mock_adapter")


class MockUniversityERPAdapter(ERPAdapterInterface):
    """Realistic Mock University ERP Adapter.
    Simulates a university financial ERP system (such as Ellucian Banner / Workday AP module).
    Provides realistic document reference generation, double-entry validation,
    controlled error simulation, and idempotent processing.
    """

    adapter_name: str = "MOCK_UNIVERSITY_ERP"

    def __init__(self):
        self._idempotency_cache: Dict[str, Dict[str, Any]] = {}

    def get_connection_status(self) -> Dict[str, Any]:
        """Returns mock ERP health telemetry."""
        return {
            "adapter_name": self.adapter_name,
            "connection_type": "MOCK",
            "is_connected": True,
            "latency_ms": 24,
            "supported_features": [
                "DOUBLE_ENTRY_VOUCHER_POSTING",
                "DOCUMENT_REVERSAL",
                "REALTIME_BUDGET_ENCUMBRANCE",
                "IDEMPOTENCY_VERIFICATION",
                "GST_INPUT_CREDIT_BREAKDOWN",
            ],
            "server_version": "Mock-UniERP v4.2.1-edu",
            "system_time": datetime.now(timezone.utc).isoformat(),
            "notice": "Simulated University ERP Engine. Fully operational in mock mode.",
        }

    def post_invoice(
        self,
        journal_entry: JournalEntry,
        invoice: Invoice,
        idempotency_key: str,
        simulate_failure: bool = False,
    ) -> Dict[str, Any]:
        """Submits balanced journal entry to the Mock ERP."""
        start_time = time.time()
        logger.info(
            f"[{self.adapter_name}] Received posting request for Invoice #{invoice.invoice_number} "
            f"(Entry #{journal_entry.entry_number}, IdempotencyKey: {idempotency_key})"
        )

        # 1. Idempotency Check
        if idempotency_key in self._idempotency_cache:
            logger.info(f"[{self.adapter_name}] Idempotency cache hit for key {idempotency_key}")
            cached = self._idempotency_cache[idempotency_key]
            cached["idempotent_replay"] = True
            return cached

        # 2. Controlled Failure Simulation for Testing
        if simulate_failure:
            logger.warning(f"[{self.adapter_name}] Simulated ERP connection failure triggered for testing.")
            return {
                "success": False,
                "error_code": "ERP_GATEWAY_TIMEOUT",
                "error_message": "Mock ERP gateway timed out after 30000ms. Transaction rolled back.",
                "duration_ms": int((time.time() - start_time) * 1000) + 20,
            }

        # 3. Double-entry balance check
        if not journal_entry.is_balanced or journal_entry.total_debit != journal_entry.total_credit:
            logger.error(
                f"[{self.adapter_name}] Journal entry rejected: Debits ({journal_entry.total_debit}) "
                f"!= Credits ({journal_entry.total_credit})"
            )
            return {
                "success": False,
                "error_code": "ERP_UNBALANCED_VOUCHER",
                "error_message": f"Debit total ({journal_entry.total_debit}) does not equal Credit total ({journal_entry.total_credit}).",
                "duration_ms": int((time.time() - start_time) * 1000),
            }

        # 4. Generate Deterministic Unique ERP Reference
        year = journal_entry.posting_date.year if journal_entry.posting_date else datetime.now().year
        raw_hash = hashlib.sha256(f"{invoice.id}-{journal_entry.entry_number}-{idempotency_key}".encode()).hexdigest()[:6].upper()
        doc_ref = f"MOCK-ERP-DOC-{year}-{invoice.id:04d}-{raw_hash}"

        # 5. Build Successful Response Payload
        duration_ms = max(15, int((time.time() - start_time) * 1000) + 12)
        response_data = {
            "success": True,
            "adapter": self.adapter_name,
            "erp_document_reference": doc_ref,
            "voucher_number": f"VOUCHER-{year}-{invoice.id:05d}",
            "fiscal_year": f"FY{year}",
            "accounting_period": journal_entry.accounting_period,
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "total_posted_debit": float(journal_entry.total_debit),
            "total_posted_credit": float(journal_entry.total_credit),
            "lines_posted_count": len(journal_entry.lines) if journal_entry.lines else 0,
            "gl_batch_id": f"GL-BATCH-{year}-{raw_hash}",
            "duration_ms": duration_ms,
            "idempotent_replay": False,
        }

        # Cache for idempotency
        self._idempotency_cache[idempotency_key] = response_data
        return response_data

    def reverse_posting(
        self,
        erp_document_reference: str,
        reversal_journal_entry: JournalEntry,
    ) -> Dict[str, Any]:
        """Simulates reversal of an existing ERP voucher."""
        logger.info(f"[{self.adapter_name}] Reversing ERP Document #{erp_document_reference}")
        year = reversal_journal_entry.posting_date.year if reversal_journal_entry.posting_date else datetime.now().year
        reversal_doc_ref = f"REV-{erp_document_reference}"

        return {
            "success": True,
            "adapter": self.adapter_name,
            "original_erp_document_reference": erp_document_reference,
            "reversal_erp_document_reference": reversal_doc_ref,
            "reversal_voucher_number": f"REV-VOUCHER-{year}-{reversal_journal_entry.id:05d}",
            "reversed_at": datetime.now(timezone.utc).isoformat(),
            "status": "REVERSED",
        }

    def check_posting_status(self, erp_document_reference: str) -> Dict[str, Any]:
        """Simulates checking posting status in mock ERP."""
        return {
            "adapter": self.adapter_name,
            "erp_document_reference": erp_document_reference,
            "status": "SYNCED",
            "last_verified_at": datetime.now(timezone.utc).isoformat(),
        }
