from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.fraud_alert import FraudAlert
from app.models.audit_log import AuditLog
from app.schemas.fraud_alert import FraudAlertResolve, FraudAlertResponse

router = APIRouter(prefix="/fraud-alerts", tags=["Fraud & Exceptions"])


@router.get("", response_model=List[FraudAlertResponse])
def list_fraud_alerts(
    status: Optional[str] = Query(None, description="Filter by status (OPEN, UNDER_REVIEW, RESOLVED, DISMISSED)"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    invoice_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List fraud alerts and exception flags."""
    query = db.query(FraudAlert).options(joinedload(FraudAlert.resolver))
    if status:
        query = query.filter(FraudAlert.status == status.upper())
    if severity:
        query = query.filter(FraudAlert.severity == severity.upper())
    if invoice_id:
        query = query.filter(FraudAlert.invoice_id == invoice_id)

    return query.order_by(FraudAlert.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/{alert_id}/resolve", response_model=FraudAlertResponse)
def resolve_fraud_alert(
    alert_id: int,
    resolve_data: FraudAlertResolve,
    db: Session = Depends(get_db),
):
    """Resolve or dismiss a fraud alert."""
    alert = db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Fraud alert not found")

    old_status = alert.status
    alert.status = resolve_data.status.upper()
    alert.resolved_by = resolve_data.resolved_by
    alert.resolved_at = datetime.now(timezone.utc)

    audit = AuditLog(
        action=f"FRAUD_ALERT_{alert.status}",
        entity_type="FRAUD_ALERT",
        entity_id=str(alert.id),
        user_id=alert.resolved_by,
        old_values={"status": old_status},
        new_values={"status": alert.status},
    )
    db.add(audit)
    db.commit()
    db.refresh(alert)
    return alert

