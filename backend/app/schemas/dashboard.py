from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import BaseModel
from app.schemas.invoice import InvoiceResponse
from app.schemas.audit_log import AuditLogResponse
from app.schemas.fraud_alert import FraudAlertResponse


class DepartmentBudgetSummary(BaseModel):
    department_id: int
    department_name: str
    department_code: str
    allocated_amount: Decimal
    committed_amount: Decimal
    spent_amount: Decimal
    available_amount: Decimal
    utilization_percentage: float


class DashboardSummaryResponse(BaseModel):
    total_invoices: int
    pending_approvals: int
    invoices_under_review: int
    exceptions_detected: int
    total_payable_amount: Decimal
    scheduled_payments_amount: Decimal
    total_budget_allocated: Decimal
    total_budget_spent: Decimal
    total_budget_committed: Decimal
    total_budget_available: Decimal
    overall_budget_utilization: float
    department_budgets: List[DepartmentBudgetSummary]
    workflow_status_counts: Dict[str, int]
    recent_invoices: List[InvoiceResponse]
    recent_audit_activity: List[AuditLogResponse]
    recent_fraud_alerts: List[FraudAlertResponse]

