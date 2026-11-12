from typing import Any, Dict
from app.models.invoice import Invoice
from app.models.journal_entry import JournalEntry
from app.services.erp.adapters.base import ERPAdapterInterface


class GenericRESTAdapter(ERPAdapterInterface):
    """Generic REST ERP Adapter for standard JSON webhooks and external accounting APIs."""

    adapter_name: str = "GENERIC_REST_ERP_ADAPTER"

    def get_connection_status(self) -> Dict[str, Any]:
        return {
            "adapter_name": self.adapter_name,
            "connection_type": "WEBHOOK_REST",
            "is_connected": False,
            "latency_ms": 0,
            "supported_features": ["JSON_PAYLOAD_SYNC", "WEBHOOK_CALLBACKS"],
            "notice": "Generic REST adapter requires target webhook URL configuration.",
        }

    def post_invoice(
        self,
        journal_entry: JournalEntry,
        invoice: Invoice,
        idempotency_key: str,
        simulate_failure: bool = False,
    ) -> Dict[str, Any]:
        return {
            "success": False,
            "error_code": "GENERIC_REST_NOT_CONFIGURED",
            "error_message": "Generic REST endpoint not configured.",
        }

    def reverse_posting(self, erp_document_reference: str, reversal_journal_entry: JournalEntry) -> Dict[str, Any]:
        return {"success": False, "error_code": "GENERIC_REST_NOT_CONFIGURED"}

    def check_posting_status(self, erp_document_reference: str) -> Dict[str, Any]:
        return {"status": "UNAVAILABLE"}
