from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.department import DepartmentResponse


class BudgetBase(BaseModel):
    department_id: int
    fiscal_year: str
    allocated_amount: Decimal = Field(..., ge=0)
    committed_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    spent_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    available_amount: Decimal = Field(..., ge=0)


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    allocated_amount: Optional[Decimal] = Field(None, ge=0)
    committed_amount: Optional[Decimal] = Field(None, ge=0)
    spent_amount: Optional[Decimal] = Field(None, ge=0)
    available_amount: Optional[Decimal] = Field(None, ge=0)


class BudgetResponse(BudgetBase):
    id: int
    created_at: datetime
    updated_at: datetime
    department: Optional[DepartmentResponse] = None

    model_config = ConfigDict(from_attributes=True)

