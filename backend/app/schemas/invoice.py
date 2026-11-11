from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.vendor import VendorResponse
from app.schemas.department import DepartmentResponse
from app.schemas.purchase_order import PurchaseOrderResponse
from app.schemas.approval import ApprovalResponse
from app.schemas.payment import PaymentResponse
from app.schemas.fraud_alert import FraudAlertResponse


class InvoiceLineBase(BaseModel):
    line_number: int
    description: str
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.00"), ge=0)
    line_total: Decimal = Field(..., ge=0)


class InvoiceLineCreate(InvoiceLineBase):
    pass


class InvoiceLineResponse(InvoiceLineBase):
    id: int
    invoice_id: int

    model_config = ConfigDict(from_attributes=True)


class InvoiceBase(BaseModel):
    invoice_number: str = Field(..., max_length=100)
    vendor_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    department_id: Optional[int] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    subtotal: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    total_amount: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)
    currency: str = "USD"
    description: Optional[str] = None
    tax_identifier: Optional[str] = None
    document_path: Optional[str] = None
    original_filename: Optional[str] = None
    file_hash: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    raw_text: Optional[str] = None
    ocr_method: Optional[str] = None
    confidence_score: Optional[Decimal] = None
    extraction_status: str = "PENDING"
    processing_status: str = "RECEIVED"
    approval_status: str = "PENDING"
    payment_status: str = "UNPAID"


class InvoiceCreate(InvoiceBase):
    lines: List[InvoiceLineCreate] = []


class InvoiceUpdate(BaseModel):
    processing_status: Optional[str] = None
    approval_status: Optional[str] = None
    payment_status: Optional[str] = None
    due_date: Optional[date] = None


class InvoiceReviewUpdate(BaseModel):
    """Allows staff to correct extracted invoice fields during human review."""
    vendor_id: Optional[int] = None
    department_id: Optional[int] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    purchase_order_id: Optional[int] = None
    subtotal: Optional[Decimal] = Field(None, ge=0)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    total_amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = None
    description: Optional[str] = None
    tax_identifier: Optional[str] = None


class InvoiceResponse(InvoiceBase):
    id: int
    normalized_invoice_number: str
    created_at: datetime
    updated_at: datetime
    vendor: Optional[VendorResponse] = None
    department: Optional[DepartmentResponse] = None
    lines: List[InvoiceLineResponse] = []

    model_config = ConfigDict(from_attributes=True)


class InvoiceDetailResponse(InvoiceResponse):
    purchase_order: Optional[PurchaseOrderResponse] = None
    approvals: List[ApprovalResponse] = []
    payments: List[PaymentResponse] = []
    fraud_alerts: List[FraudAlertResponse] = []
    extraction_metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceUploadResponse(BaseModel):
    invoice_id: int
    invoice_number: str
    original_filename: str
    file_hash: str
    file_size: int
    mime_type: str
    ocr_method: Optional[str] = None
    confidence_score: Optional[Decimal] = None
    processing_status: str
    extraction_status: str
    is_duplicate: bool
    duplicate_warning: Optional[str] = None
    duplicate_invoice_id: Optional[int] = None
    extracted_data: Optional[Dict[str, Any]] = None


class InvoiceValidationResponse(BaseModel):
    success: bool
    invoice_id: int
    processing_status: str
    message: str
    invoice: InvoiceDetailResponse
