from datetime import date
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.invoice import Invoice
from app.models.payment import Payment

client = TestClient(app)


def test_approvals_and_audit(db_session):
    # Ensure at least two valid payment records exist in the isolated test session
    invoices = db_session.query(Invoice).limit(2).all()
    for idx, inv in enumerate(invoices):
        pay = Payment(
            invoice_id=inv.id,
            payment_reference=f"TEST-WORKFLOW-PAY-{inv.id}-{idx + 1}",
            scheduled_date=date.today(),
            amount=Decimal("5000.00"),
            status="SCHEDULED",
            payment_method="NEFT",
        )
        db_session.add(pay)
    db_session.flush()

    # 1. Fetch approvals
    res = client.get("/api/v1/approvals")
    assert res.status_code == 200
    approvals = res.json()
    assert len(approvals) > 0

    # 2. Fetch payments
    pay_res = client.get("/api/v1/payments")
    assert pay_res.status_code == 200
    payments = pay_res.json()
    assert len(payments) >= 2

    # 3. Fetch audit logs
    audit_res = client.get("/api/v1/audit-logs")
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 5

