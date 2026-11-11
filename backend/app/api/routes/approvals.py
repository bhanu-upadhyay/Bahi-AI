from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.approval import Approval
from app.models.invoice import Invoice
from app.models.audit_log import AuditLog
from app.schemas.approval import ApprovalAction, ApprovalResponse

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("", response_model=List[ApprovalResponse])
def list_approvals(
    status: Optional[str] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED)"),
    invoice_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List approval tasks and history."""
    query = db.query(Approval).options(joinedload(Approval.approver))
    if status:
        query = query.filter(Approval.status == status.upper())
    if invoice_id:
        query = query.filter(Approval.invoice_id == invoice_id)

    return query.order_by(Approval.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/{approval_id}/action", response_model=ApprovalResponse)
def act_on_approval(
    approval_id: int,
    action: ApprovalAction,
    db: Session = Depends(get_db),
):
    """Perform approval or rejection on an approval workflow task."""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval task not found")

    new_status = action.status.upper()
    if new_status not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Status must be either APPROVED or REJECTED")

    old_status = approval.status
    approval.status = new_status
    approval.comments = action.comments or approval.comments
    approval.decided_at = datetime.now(timezone.utc)
    if action.approver_id:
        approval.approver_id = action.approver_id

    # If rejected, set invoice approval_status to REJECTED
    invoice = db.query(Invoice).filter(Invoice.id == approval.invoice_id).first()
    if invoice:
        if new_status == "REJECTED":
            invoice.approval_status = "REJECTED"
        elif new_status == "APPROVED":
            # Check if there are other pending approvals for this invoice
            pending_count = (
                db.query(Approval)
                .filter(Approval.invoice_id == invoice.id, Approval.status == "PENDING", Approval.id != approval.id)
                .count()
            )
            if pending_count == 0:
                invoice.approval_status = "APPROVED"

    # Append audit log
    audit = AuditLog(
        action=f"INVOICE_APPROVAL_{new_status}",
        entity_type="APPROVAL",
        entity_id=str(approval.id),
        user_id=approval.approver_id,
        old_values={"status": old_status},
        new_values={"status": new_status, "comments": approval.comments},
    )
    db.add(audit)
    db.commit()
    db.refresh(approval)
    return approval

