from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class VendorBase(BaseModel):
    vendor_code: str = Field(..., max_length=50)
    legal_name: str = Field(..., max_length=200)
    contact_person: str = Field(..., max_length=150)
    email: EmailStr
    phone: str = Field(..., max_length=50)
    address: str
    tax_identifier: str = Field(..., max_length=100)
    bank_account_last_four: str = Field(..., min_length=4, max_length=4)
    bank_name: str = Field(..., max_length=150)
    is_active: bool = True


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    bank_account_last_four: Optional[str] = Field(None, min_length=4, max_length=4)
    bank_name: Optional[str] = None
    is_active: Optional[bool] = None


class VendorResponse(VendorBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

