from typing import Any, Dict
from app.models.invoice import Invoice
from app.models.journal_entry import JournalEntry
from app.services.erp.adapters.base import ERPAdapterInterface


class OracleERPAdapter(ERPAdapterInterface):
    """Stub adapter for future Oracle Fusion Cloud Financials integration.
    Currently unconfigured in prototype mode.
    """

    adapter_name: str = "ORACLE_FUSION_ERP_ADAPTER"

    def get_connection_status(self) -> Dict[str, Any]:
        return {
            "adapter_name": self.adapter_name,
            "connection_type": "LIVE_ERP_CONNECTOR",
            "is_connected": False,
            "latency_ms": 0,
            "supported_features": ["REST_INVOICE_IMPORT", "FBDI_GL_JOURNAL"],
            "notice": "Oracle Fusion Financials connector is currently dormant. Use Mock University ERP.",
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
            "error_code": "ORACLE_NOT_CONFIGURED",
            "error_message": "Oracle Fusion ERP live endpoint not configured. Please switch to Mock ERP.",
        }

    def reverse_posting(self, erp_document_reference: str, reversal_journal_entry: JournalEntry) -> Dict[str, Any]:
        return {"success": False, "error_code": "ORACLE_NOT_CONFIGURED"}

    def check_posting_status(self, erp_document_reference: str) -> Dict[str, Any]:
        return {"status": "UNAVAILABLE"}
