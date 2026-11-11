from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DepartmentBase(BaseModel):
    name: str = Field(..., max_length=150)
    code: str = Field(..., max_length=20)
    description: Optional[str] = None
    is_active: bool = True


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentResponse(DepartmentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

