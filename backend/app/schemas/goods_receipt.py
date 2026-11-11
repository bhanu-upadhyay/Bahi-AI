from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.auth import UserResponse


class GoodsReceiptLineBase(BaseModel):
    purchase_order_line_id: int
    quantity_ordered: Decimal = Field(..., ge=0)
    quantity_received: Decimal = Field(..., ge=0)
    quantity_accepted: Decimal = Field(..., ge=0)
    quantity_rejected: Decimal = Field(default=Decimal("0.00"), ge=0)
    notes: Optional[str] = None


class GoodsReceiptLineCreate(GoodsReceiptLineBase):
    pass


class GoodsReceiptLineResponse(GoodsReceiptLineBase):
    id: int
    goods_receipt_id: int

    model_config = ConfigDict(from_attributes=True)


class GoodsReceiptBase(BaseModel):
    grn_number: str = Field(..., max_length=50)
    purchase_order_id: int
    received_date: date
    status: str = "RECEIVED"
    notes: Optional[str] = None


class GoodsReceiptCreate(GoodsReceiptBase):
    received_by: int
    lines: List[GoodsReceiptLineCreate] = []


class GoodsReceiptResponse(GoodsReceiptBase):
    id: int
    received_by: int
    created_at: datetime
    lines: List[GoodsReceiptLineResponse] = []
    receiver: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)

