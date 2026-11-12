from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# -------------------------------------------------------------
# Chart of Accounts Schemas
# -------------------------------------------------------------
class ChartOfAccountBase(BaseModel):
    account_code: str = Field(..., max_length=20)
    account_name: str = Field(..., max_length=150)
    account_type: str = Field(..., max_length=50)  # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
    description: Optional[str] = None
    is_active: bool = True


class ChartOfAccountCreate(ChartOfAccountBase):
    pass


class ChartOfAccountResponse(ChartOfAccountBase):
    id: int
    created_at: datetime
    updated_at: datetime
    debit_balance: Decimal = Decimal("0.00")
    credit_balance: Decimal = Decimal("0.00")
    net_balance: Decimal = Decimal("0.00")

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Account Mapping Schemas
# -------------------------------------------------------------
class AccountMappingBase(BaseModel):
    mapping_type: str = Field(..., max_length=50)
    entity_id: Optional[int] = None
    expense_category: Optional[str] = None
    debit_account_id: int
    credit_account_id: Optional[int] = None
    description: Optional[str] = None
    is_active: bool = True


class AccountMappingCreate(AccountMappingBase):
    pass


class AccountMappingUpdate(BaseModel):
    debit_account_id: Optional[int] = None
    credit_account_id: Optional[int] = None
    expense_category: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class AccountMappingResponse(AccountMappingBase):
    id: int
    debit_account: Optional[ChartOfAccountResponse] = None
    credit_account: Optional[ChartOfAccountResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Journal Entry Schemas
# -------------------------------------------------------------
class JournalEntryLineResponse(BaseModel):
    id: int
    journal_entry_id: int
    line_number: int
    account_id: int
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    account_type: Optional[str] = None
    description: str
    debit_amount: Decimal
    credit_amount: Decimal
    department_id: Optional[int] = None
    vendor_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class JournalEntryResponse(BaseModel):
    id: int
    entry_number: str
    invoice_id: Optional[int] = None
    posting_date: date
    accounting_period: str
    description: str
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool
    status: str  # POSTED, REVERSED, DRAFT
    reversal_of_id: Optional[int] = None
    erp_document_reference: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JournalEntryDetailResponse(JournalEntryResponse):
    lines: List[JournalEntryLineResponse] = []


# -------------------------------------------------------------
# Trial Balance Schemas
# -------------------------------------------------------------
class TrialBalanceAccount(BaseModel):
    account_id: int
    account_code: str
    account_name: str
    account_type: str
    debit_total: Decimal
    credit_total: Decimal
    net_debit: Decimal
    net_credit: Decimal


class TrialBalanceResponse(BaseModel):
    accounting_period: Optional[str] = None
    as_of_date: date
    accounts: List[TrialBalanceAccount] = []
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool


# -------------------------------------------------------------
# ERP Posting & Eligibility Schemas
# -------------------------------------------------------------
class PostingEligibilityCheck(BaseModel):
    check_name: str
    passed: bool
    message: str
    severity: str = "ERROR"  # ERROR, WARNING, INFO


class PostingEligibilityResponse(BaseModel):
    invoice_id: int
    eligible: bool
    human_approved: bool
    already_posted: bool
    checks: List[PostingEligibilityCheck] = []
    blocking_reasons: List[str] = []
    warnings: List[str] = []


class ERPPostingRequest(BaseModel):
    idempotency_key: Optional[str] = None
    simulate_failure: bool = False
    comments: Optional[str] = None


class ERPPostingResponse(BaseModel):
    id: int
    invoice_id: int
    journal_entry_id: Optional[int] = None
    erp_adapter: str
    erp_document_reference: str
    idempotency_key: str
    status: str
    posted_at: Optional[datetime] = None
    error_message: Optional[str] = None
    response_payload: Optional[Dict[str, Any]] = None
    journal_entry: Optional[JournalEntryResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ERPSyncLogResponse(BaseModel):
    id: int
    erp_posting_id: Optional[int] = None
    invoice_id: Optional[int] = None
    action: str
    status: str
    request_payload: Optional[Dict[str, Any]] = None
    response_payload: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ERPConnectionStatusResponse(BaseModel):
    adapter_name: str
    connection_type: str  # MOCK, LIVE, SANDBOX
    is_connected: bool
    latency_ms: int
    supported_features: List[str]
    active_postings_count: int
    pending_sync_count: int
    failed_sync_count: int
    system_time: datetime
    notice: str = "Connected to Mock University ERP (Simulated Environment). No live ERP/bank connection."


# -------------------------------------------------------------
# Payment Extensions Schemas
# -------------------------------------------------------------
class InvoicePaymentBalanceResponse(BaseModel):
    invoice_id: int
    invoice_number: str
    total_invoiced_amount: Decimal
    total_paid_amount: Decimal
    outstanding_balance: Decimal
    is_fully_paid: bool
    payment_status: str
    payments: List[Dict[str, Any]] = []


class PaymentPreparationRequest(BaseModel):
    invoice_id: int
    amount: Decimal = Field(..., gt=0)
    scheduled_date: date
    payment_method: str = "ACH"  # ACH, WIRE, CHECK, INTERNAL_TRANSFER
    comments: Optional[str] = None


class PaymentPreparationResponse(BaseModel):
    payment_id: int
    invoice_id: int
    payment_reference: str
    amount: Decimal
    scheduled_date: date
    payment_method: str
    status: str
    remaining_balance_after: Decimal
    message: str
