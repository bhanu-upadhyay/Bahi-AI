from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import FINANCE_ROLES, require_roles
from app.models.erp_posting import ERPPosting, ERPSyncLog
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.erp import (
    ERPConnectionStatusResponse,
    ERPPostingRequest,
    ERPPostingResponse,
    ERPSyncLogResponse,
    PostingEligibilityResponse,
)
from app.services.erp.adapters import get_erp_adapter
from app.services.erp.posting_service import PostingService
from app.services.erp.sync_service import SyncService

router = APIRouter(prefix="/erp", tags=["ERP Integration"])


@router.get("/status", response_model=ERPConnectionStatusResponse)
def get_erp_connection_status(db: Session = Depends(get_db)):
    """Returns the operational status of the ERP integration."""
    adapter = get_erp_adapter("MOCK_UNIVERSITY_ERP")
    adapter_status = adapter.get_connection_status()

    total_postings = db.query(ERPPosting).filter(ERPPosting.status == "SYNCED").count()
    pending_sync = db.query(ERPPosting).filter(ERPPosting.status.in_(["PENDING", "QUEUED", "RETRY_PENDING"])).count()
    failed_sync = db.query(ERPPosting).filter(ERPPosting.status == "FAILED").count()

    return ERPConnectionStatusResponse(
        adapter_name=adapter_status["adapter_name"],
        connection_type=adapter_status["connection_type"],
        is_connected=adapter_status["is_connected"],
        latency_ms=adapter_status.get("latency_ms", 20),
        supported_features=adapter_status.get("supported_features", []),
        active_postings_count=total_postings,
        pending_sync_count=pending_sync,
        failed_sync_count=failed_sync,
        system_time=datetime.now(timezone.utc),
        notice=adapter_status.get("notice", "Connected to Mock University ERP."),
    )


@router.get("/config")
def get_erp_configuration():
    """Returns active ERP integration parameters and supported adapters."""
    return {
        "active_adapter": "MOCK_UNIVERSITY_ERP",
        "available_adapters": [
            {"id": "MOCK_UNIVERSITY_ERP", "name": "Mock University ERP", "status": "ACTIVE", "is_mock": True},
            {"id": "SAP", "name": "SAP S/4HANA Finance", "status": "PLANNED_FUTURE", "is_mock": False},
            {"id": "ORACLE", "name": "Oracle Fusion Cloud ERP", "status": "PLANNED_FUTURE", "is_mock": False},
            {"id": "GENERIC_REST", "name": "Generic REST / Webhook ERP", "status": "PLANNED_FUTURE", "is_mock": False},
        ],
        "posting_policy": "STRICT_HUMAN_APPROVAL_REQUIRED",
        "double_entry_enforcement": "MANDATORY_BALANCED_DEBITS_CREDITS",
    }


@router.get("/eligibility/{invoice_id}", response_model=PostingEligibilityResponse)
def check_invoice_posting_eligibility(invoice_id: int, db: Session = Depends(get_db)):
    """Evaluates all strict pre-requisites required to post an invoice to the ERP."""
    service = PostingService()
    return service.check_eligibility(invoice_id=invoice_id, db=db)


@router.post("/post/{invoice_id}", response_model=ERPPostingResponse)
def post_invoice_to_erp(
    invoice_id: int,
    payload: Optional[ERPPostingRequest] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(require_roles(*FINANCE_ROLES)),
):
    """Executes the complete ERP posting workflow: verifies eligibility,
    generates a balanced double-entry journal entry, dispatches to Mock ERP,
    records ERP document reference, and logs audit entries.
    Protected by RBAC: only authorized finance administrators and officers may post.
    """
    service = PostingService()
    req = payload or ERPPostingRequest()
    return service.post_invoice_to_erp(
        invoice_id=invoice_id,
        db=db,
        idempotency_key=req.idempotency_key,
        simulate_failure=req.simulate_failure,
        comments=req.comments,
    )


@router.get("/posting/{invoice_id}", response_model=ERPPostingResponse)
def get_invoice_erp_posting(invoice_id: int, db: Session = Depends(get_db)):
    """Retrieves the ERP posting details and document reference for an invoice."""
    posting = (
        db.query(ERPPosting)
        .options(
            joinedload(ERPPosting.journal_entry),
        )
        .filter(ERPPosting.invoice_id == invoice_id)
        .first()
    )
    if not posting:
        raise HTTPException(status_code=404, detail="No ERP posting record found for this invoice.")
    return posting


@router.get("/history", response_model=List[ERPPostingResponse])
def list_erp_posting_history(
    status: Optional[str] = Query(None, description="Filter by posting status: SYNCED, FAILED, PENDING"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Returns history of ERP invoice postings."""
    query = (
        db.query(ERPPosting)
        .options(
            joinedload(ERPPosting.journal_entry),
        )
    )
    if status:
        query = query.filter(ERPPosting.status == status.upper())
    return query.order_by(ERPPosting.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/sync/queue", response_model=List[ERPPostingResponse])
def get_sync_queue(db: Session = Depends(get_db)):
    """Returns all ERP transactions currently queued, pending, or requiring retry."""
    service = SyncService()
    return service.get_sync_queue(db=db)


@router.post("/sync/retry/{posting_id}", response_model=ERPPostingResponse)
def retry_failed_sync(posting_id: int, db: Session = Depends(get_db)):
    """Retries a failed ERP posting transaction safely."""
    service = SyncService()
    return service.retry_failed_posting(posting_id=posting_id, db=db)


@router.get("/sync/logs", response_model=List[ERPSyncLogResponse])
def get_sync_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Returns granular ERP synchronization telemetry and audit logs."""
    service = SyncService()
    return service.get_sync_history(db=db, limit=limit)
