import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoints():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["application"] == "Bahi-AI"

    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

    response = client.get("/api/health/database")
    assert response.status_code == 200
    assert response.json()["status"] == "connected"


def test_dashboard_summary():
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_invoices" in data
    assert data["total_invoices"] >= 10
    assert "pending_approvals" in data
    assert "exceptions_detected" in data
    assert "total_payable_amount" in data
    assert "department_budgets" in data
    assert len(data["department_budgets"]) >= 5


def test_list_invoices():
    response = client.get("/api/v1/invoices")
    assert response.status_code == 200
    invoices = response.json()
    assert len(invoices) >= 10
    # Check required fields
    first = invoices[0]
    assert "invoice_number" in first
    assert "total_amount" in first
    assert "processing_status" in first


def test_get_invoice_detail():
    # Fetch first invoice
    list_res = client.get("/api/v1/invoices")
    assert list_res.status_code == 200
    first_id = list_res.json()[0]["id"]

    detail_res = client.get(f"/api/v1/invoices/{first_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == first_id
    assert "lines" in detail
    assert "approvals" in detail
    assert "payments" in detail
    assert "fraud_alerts" in detail


def test_duplicate_invoice_prevention():
    # Attempt to create duplicate of INV-2024-001 for vendor 1
    dup_payload = {
        "invoice_number": "INV-2024-001",
        "vendor_id": 1,
        "department_id": 1,
        "invoice_date": "2024-10-15",
        "due_date": "2024-11-15",
        "subtotal": "30000.00",
        "tax_amount": "5400.00",
        "total_amount": "35400.00",
        "currency": "USD",
        "lines": [],
    }
    res = client.post("/api/v1/invoices", json=dup_payload)
    assert res.status_code == 409
    assert "duplicate" in res.json()["detail"].lower()

