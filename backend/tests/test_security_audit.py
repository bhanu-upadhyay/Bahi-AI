from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.main import app
from app.models.approval import Approval
from app.models.invoice import Invoice
from app.models.user import User
from app.services.erp.accounting_engine import AccountingEngine
from app.utils.file_handler import get_absolute_file_path

client = TestClient(app)


# --------------------------------------------------------------------------
# 1. Authentication & JWT Validation Tests
# --------------------------------------------------------------------------
def test_login_success_and_jwt_claims():
    """Verifies user login with valid credentials yields a signed JWT with role claims."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "sarah.jenkins@university.edu", "password": "BahiAI@2025!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "sarah.jenkins@university.edu"
    assert data["user"]["role"] == "FINANCE_ADMIN"


def test_login_invalid_password():
    """Verifies that incorrect passwords are rejected with 401 Unauthorized."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "sarah.jenkins@university.edu", "password": "WrongPassword123!"},
    )
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]


def test_login_unknown_user():
    """Verifies unknown email addresses return 401 Unauthorized without leaking existence."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent.hacker@university.edu", "password": "SomePassword123!"},
    )
    assert res.status_code == 401


def test_auth_me_protected_endpoint():
    """Verifies /api/v1/auth/me requires a valid Bearer token."""
    # 1. Unauthenticated request -> 401
    unauth_res = client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401

    # 2. Authenticated request -> 200 with user profile
    token = create_access_token(subject="sarah.jenkins@university.edu", role="FINANCE_ADMIN")
    auth_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert auth_res.status_code == 200
    assert auth_res.json()["email"] == "sarah.jenkins@university.edu"


# --------------------------------------------------------------------------
# 2. Role-Based Access Control (RBAC) Tests
# --------------------------------------------------------------------------
def test_rbac_vendor_cannot_approve_invoice():
    """Verifies that a user with VENDOR role cannot approve invoices (HTTP 403)."""
    vendor_token = create_access_token(subject="accounts@apexcomputing.demo", role="VENDOR")
    res = client.post(
        "/api/v1/approvals/1/action",
        headers={"Authorization": f"Bearer {vendor_token}"},
        json={"status": "APPROVED", "comments": "Vendor self-approval attempt"},
    )
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


def test_rbac_vendor_cannot_post_erp():
    """Verifies that a user with VENDOR role cannot trigger ERP postings (HTTP 403)."""
    vendor_token = create_access_token(subject="accounts@apexcomputing.demo", role="VENDOR")
    res = client.post(
        "/api/v1/erp/post/1",
        headers={"Authorization": f"Bearer {vendor_token}"},
        json={},
    )
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


def test_rbac_vendor_cannot_simulate_payment():
    """Verifies that a user with VENDOR role cannot execute payment settlements (HTTP 403)."""
    vendor_token = create_access_token(subject="accounts@apexcomputing.demo", role="VENDOR")
    res = client.post(
        "/api/v1/payments/1/simulate",
        headers={"Authorization": f"Bearer {vendor_token}"},
    )
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


# --------------------------------------------------------------------------
# 3. Path Traversal & Filesystem Security
# --------------------------------------------------------------------------
def test_path_traversal_prevention():
    """Verifies that path traversal sequences (../, absolute paths outside uploads)
    are strictly rejected with PermissionError.
    """
    with pytest.raises(PermissionError):
        get_absolute_file_path("../../.env")

    with pytest.raises(PermissionError):
        get_absolute_file_path("/etc/passwd")

    with pytest.raises(PermissionError):
        get_absolute_file_path("app/core/config.py")


def test_security_headers_present():
    """Verifies that essential HTTP security headers are set on API responses."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("X-XSS-Protection") == "1; mode=block"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# --------------------------------------------------------------------------
# 4. Financial Correctness Regression Test: Invoice #9766
# --------------------------------------------------------------------------
def test_invoice_9766_financial_and_accounting_regression():
    """Regression test for invoice #9766:
    Taxable subtotal: ₹34,300
    CGST: ₹3,087
    SGST: ₹3,087
    Total Tax: ₹6,174
    Grand Total: ₹40,474

    Expected Accounting:
    - Debit Office Supplies (5003 or 5001): ₹34,300.00
    - Debit Input CGST (1401): ₹3,087.00
    - Debit Input SGST (1402): ₹3,087.00
    - Credit Accounts Payable (2101): ₹40,474.00
    Sum of Debits == Sum of Credits (Exact Balance).
    """
    db = SessionLocal()
    try:
        engine = AccountingEngine()
        inv = Invoice(
            id=9766,
            invoice_number="9766",
            invoice_date=date(2026, 11, 11),
            subtotal=Decimal("34300.00"),
            tax_amount=Decimal("6174.00"),
            total_amount=Decimal("40474.00"),
            currency="INR",
            extraction_metadata={
                "gst_breakdown": {
                    "taxable_subtotal": "34300.00",
                    "cgst_amount": "3087.00",
                    "sgst_amount": "3087.00",
                    "total_tax": "6174.00",
                    "grand_total": "40474.00",
                }
            },
        )
        entry = engine.generate_journal_entry_for_invoice(inv, db)

        # 1. Verification of voucher balance
        assert entry.is_balanced is True
        assert entry.total_debit == Decimal("40474.00")
        assert entry.total_credit == Decimal("40474.00")
        assert entry.total_debit == entry.total_credit

        # Map account IDs to account codes
        from app.models.chart_of_account import ChartOfAccount
        coa_map = {a.id: a.account_code for a in db.query(ChartOfAccount).all()}

        # 2. Verification of statutory tax debit allocations
        cgst_lines = [l for l in entry.lines if coa_map.get(l.account_id) == "1401"]
        sgst_lines = [l for l in entry.lines if coa_map.get(l.account_id) == "1402"]
        assert len(cgst_lines) == 1
        assert len(sgst_lines) == 1
        assert cgst_lines[0].debit_amount == Decimal("3087.00")
        assert sgst_lines[0].debit_amount == Decimal("3087.00")

        # 3. Verification of expense debit allocation
        expense_lines = [l for l in entry.lines if coa_map.get(l.account_id) in ["5001", "5003"]]
        assert len(expense_lines) >= 1
        total_expense_debit = sum(l.debit_amount for l in expense_lines)
        assert total_expense_debit == Decimal("34300.00")

        # 4. Verification of Accounts Payable credit
        ap_lines = [l for l in entry.lines if coa_map.get(l.account_id) == "2101"]
        assert len(ap_lines) == 1
        assert ap_lines[0].credit_amount == Decimal("40474.00")

    finally:
        db.close()
