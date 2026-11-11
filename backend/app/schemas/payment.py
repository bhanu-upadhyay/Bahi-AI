from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PaymentBase(BaseModel):
    invoice_id: int
    payment_reference: str
    scheduled_date: date
    payment_date: Optional[date] = None
    amount: Decimal = Field(..., gt=0)
    status: str = "SCHEDULED"
    payment_method: str = "ACH"
    external_reference: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    payment_date: Optional[date] = None
    external_reference: Optional[str] = None


class PaymentResponse(PaymentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

