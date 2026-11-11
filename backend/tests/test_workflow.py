import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_approvals_and_audit():
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

