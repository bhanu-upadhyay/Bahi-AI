from decimal import Decimal
from typing import Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import (
    Invoice,
    Budget,
    Department,
    Approval,
    FraudAlert,
    Payment,
    AuditLog,
)
from app.schemas.dashboard import DashboardSummaryResponse, DepartmentBudgetSummary
from app.schemas.invoice import InvoiceResponse
from app.schemas.audit_log import AuditLogResponse
from app.schemas.fraud_alert import FraudAlertResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Computes live KPI metrics, department budget utilization, workflow status,
    and recent activity feeds directly from database records.
    """
    # 1. Total invoices count
    total_invoices = db.scalar(select(func.count(Invoice.id))) or 0

    # 2. Pending approvals (approval_status == 'PENDING' or 'IN_REVIEW')
    pending_approvals = (
        db.scalar(
            select(func.count(Invoice.id)).where(
                Invoice.approval_status.in_(["PENDING", "IN_REVIEW"])
            )
        )
        or 0
    )

    # 3. Invoices under review
    invoices_under_review = (
        db.scalar(
            select(func.count(Invoice.id)).where(Invoice.approval_status == "IN_REVIEW")
        )
        or 0
    )

    # 4. Exceptions detected (processing_status == 'EXCEPTION' or active fraud alerts)
    exceptions_detected = (
        db.scalar(
            select(func.count(FraudAlert.id)).where(
                FraudAlert.status.in_(["OPEN", "UNDER_REVIEW"])
            )
        )
        or 0
    )

    # 5. Total payable amount (approved or pending, unpaid)
    total_payable_result = db.scalar(
        select(func.coalesce(func.sum(Invoice.total_amount), Decimal("0.00"))).where(
            Invoice.payment_status.in_(["UNPAID", "SCHEDULED"])
        )
    )
    total_payable_amount = total_payable_result or Decimal("0.00")

    # 6. Scheduled payments amount
    scheduled_payments_result = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), Decimal("0.00"))).where(
            Payment.status == "SCHEDULED"
        )
    )
    scheduled_payments_amount = scheduled_payments_result or Decimal("0.00")

    # 7. Department Budgets
    budgets = (
        db.query(Budget)
        .options(joinedload(Budget.department))
        .all()
    )

    total_allocated = Decimal("0.00")
    total_spent = Decimal("0.00")
    total_committed = Decimal("0.00")
    total_available = Decimal("0.00")
    dept_summaries: List[DepartmentBudgetSummary] = []

    for b in budgets:
        total_allocated += b.allocated_amount
        total_spent += b.spent_amount
        total_committed += b.committed_amount
        total_available += b.available_amount

        utilization = 0.0
        if b.allocated_amount > Decimal("0.00"):
            utilization = float(((b.spent_amount + b.committed_amount) / b.allocated_amount) * 100)

        dept_summaries.append(
            DepartmentBudgetSummary(
                department_id=b.department_id,
                department_name=b.department.name if b.department else f"Dept {b.department_id}",
                department_code=b.department.code if b.department else "N/A",
                allocated_amount=b.allocated_amount,
                committed_amount=b.committed_amount,
                spent_amount=b.spent_amount,
                available_amount=b.available_amount,
                utilization_percentage=round(utilization, 2),
            )
        )

    overall_utilization = 0.0
    if total_allocated > Decimal("0.00"):
        overall_utilization = float(((total_spent + total_committed) / total_allocated) * 100)

    # 8. Workflow status counts
    status_records = (
        db.query(Invoice.processing_status, func.count(Invoice.id))
        .group_by(Invoice.processing_status)
        .all()
    )
    workflow_counts: Dict[str, int] = {
        "RECEIVED": 0,
        "PROCESSING": 0,
        "MATCHED": 0,
        "EXCEPTION": 0,
        "DUPLICATE": 0,
    }
    for st, count in status_records:
        workflow_counts[st] = count

    # 9. Recent invoices (latest 5)
    recent_invoices_raw = (
        db.query(Invoice)
        .options(joinedload(Invoice.vendor), joinedload(Invoice.department))
        .order_by(Invoice.created_at.desc())
        .limit(6)
        .all()
    )
    recent_invoices = [InvoiceResponse.model_validate(inv) for inv in recent_invoices_raw]

    # 10. Recent audit activity
    recent_audit_raw = (
        db.query(AuditLog)
        .options(joinedload(AuditLog.user))
        .order_by(AuditLog.created_at.desc())
        .limit(6)
        .all()
    )
    recent_audit_activity = [AuditLogResponse.model_validate(a) for a in recent_audit_raw]

    # 11. Recent fraud alerts
    recent_fraud_raw = (
        db.query(FraudAlert)
        .order_by(FraudAlert.created_at.desc())
        .limit(5)
        .all()
    )
    recent_fraud_alerts = [FraudAlertResponse.model_validate(f) for f in recent_fraud_raw]

    return DashboardSummaryResponse(
        total_invoices=total_invoices,
        pending_approvals=pending_approvals,
        invoices_under_review=invoices_under_review,
        exceptions_detected=exceptions_detected,
        total_payable_amount=total_payable_amount,
        scheduled_payments_amount=scheduled_payments_amount,
        total_budget_allocated=total_allocated,
        total_budget_spent=total_spent,
        total_budget_committed=total_committed,
        total_budget_available=total_available,
        overall_budget_utilization=round(overall_utilization, 2),
        department_budgets=dept_summaries,
        workflow_status_counts=workflow_counts,
        recent_invoices=recent_invoices,
        recent_audit_activity=recent_audit_activity,
        recent_fraud_alerts=recent_fraud_alerts,
    )

