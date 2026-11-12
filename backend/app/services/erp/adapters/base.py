from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.models.invoice import Invoice
from app.models.journal_entry import JournalEntry


class ERPAdapterInterface(ABC):
    """Abstract interface for ERP adapters.
    Allows swappable implementations (Mock University ERP, SAP, Oracle, Generic REST)
    without modifying core invoice processing or AP business logic.
    """

    adapter_name: str = "BASE_ERP_ADAPTER"

    @abstractmethod
    def get_connection_status(self) -> Dict[str, Any]:
        """Returns ERP connection health, latency, adapter name, and supported features."""
        pass

    @abstractmethod
    def post_invoice(
        self,
        journal_entry: JournalEntry,
        invoice: Invoice,
        idempotency_key: str,
        simulate_failure: bool = False,
    ) -> Dict[str, Any]:
        """Submits a balanced journal entry to the external ERP system.
        Returns a dictionary containing:
          - success: bool
          - erp_document_reference: str
          - posted_at: str (ISO)
          - fiscal_year: str
          - accounting_period: str
          - raw_response: Dict[str, Any]
          - error_message: Optional[str]
        """
        pass

    @abstractmethod
    def reverse_posting(
        self,
        erp_document_reference: str,
        reversal_journal_entry: JournalEntry,
    ) -> Dict[str, Any]:
        """Requests a reversal of a previously posted ERP document."""
        pass

    @abstractmethod
    def check_posting_status(self, erp_document_reference: str) -> Dict[str, Any]:
        """Queries the ERP system for the status of a specific document reference."""
        pass
