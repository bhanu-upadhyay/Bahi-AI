from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.auth import UserResponse


class ApprovalBase(BaseModel):
    invoice_id: int
    approval_level: int = 1
    status: str = "PENDING"
    comments: Optional[str] = None


class ApprovalCreate(ApprovalBase):
    approver_id: int


class ApprovalAction(BaseModel):
    status: str  # "APPROVED" or "REJECTED"
    comments: Optional[str] = None
    approver_id: Optional[int] = None


class ApprovalResponse(ApprovalBase):
    id: int
    approver_id: int
    decided_at: Optional[datetime] = None
    created_at: datetime
    approver: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)

