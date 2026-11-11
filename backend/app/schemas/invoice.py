from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
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
    vendor_id: int
    purchase_order_id: Optional[int] = None
    department_id: int
    invoice_date: date
    due_date: date
    subtotal: Decimal = Field(..., ge=0)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    total_amount: Decimal = Field(..., ge=0)
    currency: str = "USD"
    document_path: Optional[str] = None
    original_filename: Optional[str] = None
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

    model_config = ConfigDict(from_attributes=True)

