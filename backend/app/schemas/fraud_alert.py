from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.auth import UserResponse


class FraudAlertBase(BaseModel):
    invoice_id: int
    alert_type: str
    severity: str
    description: str
    risk_score: Decimal
    status: str = "OPEN"


class FraudAlertResponse(FraudAlertBase):
    id: int
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    resolver: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


class FraudAlertResolve(BaseModel):
    status: str = "RESOLVED"  # "RESOLVED" or "DISMISSED"
    resolved_by: Optional[int] = None

