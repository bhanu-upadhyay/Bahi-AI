from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.auth import UserResponse


class AuditLogBase(BaseModel):
    user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: str
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase):
    id: int
    created_at: datetime
    user: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)

