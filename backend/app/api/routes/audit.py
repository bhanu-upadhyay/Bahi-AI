from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=List[AuditLogResponse])
def list_audit_logs(
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieve immutable, append-only system audit log entries."""
    query = db.query(AuditLog).options(joinedload(AuditLog.user))
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type.upper())
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))

    return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

