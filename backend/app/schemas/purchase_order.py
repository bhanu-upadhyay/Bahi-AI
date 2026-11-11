from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.vendor import VendorResponse
from app.schemas.department import DepartmentResponse


class PurchaseOrderLineBase(BaseModel):
    line_number: int
    item_description: str
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.00"), ge=0)
    total_amount: Decimal = Field(..., ge=0)


class PurchaseOrderLineCreate(PurchaseOrderLineBase):
    pass


class PurchaseOrderLineResponse(PurchaseOrderLineBase):
    id: int
    purchase_order_id: int

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderBase(BaseModel):
    po_number: str = Field(..., max_length=50)
    vendor_id: int
    department_id: int
    issue_date: date
    expected_delivery_date: Optional[date] = None
    total_amount: Decimal = Field(..., ge=0)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    status: str = "ISSUED"


class PurchaseOrderCreate(PurchaseOrderBase):
    created_by: int
    lines: List[PurchaseOrderLineCreate] = []


class PurchaseOrderResponse(PurchaseOrderBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    lines: List[PurchaseOrderLineResponse] = []
    vendor: Optional[VendorResponse] = None
    department: Optional[DepartmentResponse] = None

    model_config = ConfigDict(from_attributes=True)

