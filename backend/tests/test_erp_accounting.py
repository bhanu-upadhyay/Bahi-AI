from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.approval import Approval
from app.models.audit_log import AuditLog
from app.models.chart_of_account import ChartOfAccount
from app.models.erp_posting import ERPPosting, ERPSyncLog
from app.models.invoice import Invoice, InvoiceLine
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.payment import Payment
from app.models.vendor import Vendor
from app.services.erp.accounting_engine import AccountingEngine
from app.services.erp.adapters.mock_erp import MockUniversityERPAdapter
from app.services.erp.posting_service import PostingService
from app.services.erp.sync_service import SyncService

client = TestClient(app)


# -------------------------------------------------------------
# 1. Accounting Engine Tests (Double-Entry, Balancing, Tax Allocation)
# -------------------------------------------------------------
def test_double_entry_journal_balancing_with_gst():
    """Verifies that double-entry journal vouchers are balanced (Debit == Credit)
    with CGST and SGST statutory input credits.
    """
    db = SessionLocal()
    try:
        engine = AccountingEngine()
        inv = Invoice(
            id=88001,
            invoice_number="INV-GST-BALANCED",
            invoice_date=date(2026, 11, 10),
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

        assert entry.is_balanced is True
        assert entry.total_debit == entry.total_credit == Decimal("40474.00")
        assert len(entry.lines) >= 3

        # Check line accounts
        ap_lines = [l for l in entry.lines if l.credit_amount > Decimal("0.00")]
        debit_lines = [l for l in entry.lines if l.debit_amount > Decimal("0.00")]

        assert len(ap_lines) == 1
        assert ap_lines[0].credit_amount == Decimal("40474.00")
        assert sum(l.debit_amount for l in debit_lines) == Decimal("40474.00")
    finally:
        db.close()


def test_double_entry_with_igst_and_item_lines():
    """Verifies IGST allocation and multi-item line distributions to IT and Equipment accounts."""
    db = SessionLocal()
    try:
        engine = AccountingEngine()
        inv = Invoice(
            id=88002,
            invoice_number="INV-IGST-MULTI",
            invoice_date=date(2026, 11, 12),
            subtotal=Decimal("50000.00"),
            tax_amount=Decimal("9000.00"),
            total_amount=Decimal("59000.00"),
            currency="INR",
            extraction_metadata={
                "gst_breakdown": {
                    "taxable_subtotal": "50000.00",
                    "igst_amount": "9000.00",
                    "total_tax": "9000.00",
                    "grand_total": "59000.00",
                }
            },
        )
        inv.lines = [
            InvoiceLine(
                id=1,
                invoice_id=88002,
                line_number=1,
                description="Dell Precision Workstation Computer",
                quantity=Decimal("1.00"),
                unit_price=Decimal("30000.00"),
                line_total=Decimal("30000.00"),
            ),
            InvoiceLine(
                id=2,
                invoice_id=88002,
                line_number=2,
                description="Laboratory Testing Hardware Equipment",
                quantity=Decimal("2.00"),
                unit_price=Decimal("10000.00"),
                line_total=Decimal("20000.00"),
            ),
        ]

        entry = engine.generate_journal_entry_for_invoice(inv, db)
        assert entry.is_balanced is True
        assert entry.total_debit == entry.total_credit == Decimal("59000.00")

        # Verify IGST line exists
        igst_acc = db.query(ChartOfAccount).filter(ChartOfAccount.account_code == "1403").first()
        igst_line = [l for l in entry.lines if l.account_id == igst_acc.id]
        assert len(igst_line) == 1
        assert igst_line[0].debit_amount == Decimal("9000.00")
    finally:
        db.close()


def test_fractional_rounding_adjustment():
    """Verifies that minor fractional discrepancies (e.g. ₹0.02) are balanced via account 5099."""
    db = SessionLocal()
    try:
        engine = AccountingEngine()
        inv = Invoice(
            id=88003,
            invoice_number="INV-ROUNDING-DIFF",
            invoice_date=date(2026, 11, 10),
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("18.00"),
            total_amount=Decimal("118.02"),  # 2 paise rounding difference
            currency="INR",
        )
        entry = engine.generate_journal_entry_for_invoice(inv, db)
        assert entry.is_balanced is True
        assert entry.total_debit == entry.total_credit == Decimal("118.02")

        roundoff_acc = db.query(ChartOfAccount).filter(ChartOfAccount.account_code == "5099").first()
        round_line = [l for l in entry.lines if l.account_id == roundoff_acc.id]
        assert len(round_line) == 1
        assert round_line[0].debit_amount == Decimal("0.02")
    finally:
        db.close()


def test_reversal_journal_entry():
    """Verifies that reversal entries invert debits and credits and update original status to REVERSED."""
    db = SessionLocal()
    try:
        engine = AccountingEngine()
        inv = Invoice(
            id=88004,
            invoice_number="INV-REVERSAL-TEST",
            invoice_date=date(2026, 11, 10),
            subtotal=Decimal("5000.00"),
            tax_amount=Decimal("900.00"),
            total_amount=Decimal("5900.00"),
            currency="INR",
        )
        original = engine.generate_journal_entry_for_invoice(inv, db)
        assert original.status == "POSTED"

        reversal = engine.generate_reversal_entry(original, db, reason="Invoice billed in error")
        assert reversal.is_balanced is True
        assert reversal.total_debit == original.total_credit == Decimal("5900.00")
        assert reversal.reversal_of_id == original.id
        assert original.status == "REVERSED"
        assert reversal.status == "POSTED"
    finally:
        db.close()


# -------------------------------------------------------------
# 2. ERP Posting Eligibility & Workflow Tests
# -------------------------------------------------------------
def test_posting_eligibility_rejects_unapproved_invoice():
    """Rule: Invoices must not be posted unless formally approved by human officer."""
    db = SessionLocal()
    try:
        service = PostingService()

        # Invoice 1 in DB has approval_status PENDING
        inv_pending = db.query(Invoice).filter(Invoice.approval_status == "PENDING").first()
        if inv_pending:
            eligibility = service.check_eligibility(inv_pending.id, db)
            assert eligibility.eligible is False
            assert eligibility.human_approved is False
            assert any("pending human approval" in r.lower() for r in eligibility.blocking_reasons)

            # Attempting to post raises HTTP 400
            with pytest.raises(Exception) as excinfo:
                service.post_invoice_to_erp(inv_pending.id, db)
            assert "400" in str(excinfo.value) or "eligible" in str(excinfo.value)
    finally:
        db.close()


def test_posting_approved_invoice_and_idempotency():
    """Verifies end-to-end ERP posting of an approved invoice, document reference generation,
    and duplicate posting prevention using idempotency keys.
    """
    db = SessionLocal()
    try:
        service = PostingService()

        # Find an approved invoice (or Invoice 2 which is approved)
        inv = db.query(Invoice).filter(Invoice.id == 2).first()
        assert inv is not None

        # Ensure invoice is marked APPROVED for test
        inv.approval_status = "APPROVED"
        # Ensure not already posted
        db.query(ERPPosting).filter(ERPPosting.invoice_id == inv.id).delete()
        db.commit()

        # Check eligibility
        eligibility = service.check_eligibility(inv.id, db)
        assert eligibility.eligible is True
        assert eligibility.human_approved is True

        # Post to ERP
        idemp_key = f"TEST-IDEMP-{inv.id}-{datetime.now().timestamp()}"
        posting = service.post_invoice_to_erp(
            invoice_id=inv.id,
            db=db,
            idempotency_key=idemp_key,
        )

        assert posting.status == "SYNCED"
        assert posting.erp_document_reference.startswith("MOCK-ERP-DOC-")
        assert posting.journal_entry_id is not None
        assert inv.processing_status == "POSTED"

        # Verify idempotency: calling again with same key returns identical record without duplicates
        replay = service.post_invoice_to_erp(
            invoice_id=inv.id,
            db=db,
            idempotency_key=idemp_key,
        )
        assert replay.id == posting.id
        assert replay.erp_document_reference == posting.erp_document_reference
    finally:
        db.close()


def test_posting_simulation_failure_and_retry():
    """Verifies that simulated ERP failure is captured cleanly in sync logs and can be retried."""
    db = SessionLocal()
    try:
        service = PostingService()
        sync_service = SyncService()

        inv = db.query(Invoice).filter(Invoice.id == 2).first()
        assert inv is not None
        inv.approval_status = "APPROVED"

        # Clear existing posting
        db.query(ERPPosting).filter(ERPPosting.invoice_id == inv.id).delete()
        db.commit()

        # 1. Post with simulate_failure=True -> expect failure
        with pytest.raises(Exception):
            service.post_invoice_to_erp(
                invoice_id=inv.id,
                db=db,
                idempotency_key=f"FAIL-KEY-{inv.id}",
                simulate_failure=True,
            )

        # Verify failed posting recorded
        failed_posting = db.query(ERPPosting).filter(ERPPosting.invoice_id == inv.id).first()
        assert failed_posting is not None
        assert failed_posting.status == "FAILED"
        assert "timed out" in failed_posting.error_message.lower()

        # 2. Retry the failed posting -> expect success
        recovered = sync_service.retry_failed_posting(failed_posting.id, db)
        assert recovered.status == "SYNCED"
        assert recovered.erp_document_reference.startswith("MOCK-ERP-DOC-")
        assert recovered.error_message is None
    finally:
        db.close()


# -------------------------------------------------------------
# 3. Payments, Partial Settlements, and Balance Tracking Tests
# -------------------------------------------------------------
def test_payment_balance_tracking_and_partial_settlement():
    """Verifies partial disbursements, remaining balance calculations,
    and prevention of payments exceeding outstanding balance.
    """
    db = SessionLocal()
    try:
        inv = db.query(Invoice).filter(Invoice.id == 2).first()
        assert inv is not None
        inv.approval_status = "APPROVED"
        inv.payment_status = "UNPAID"
        # Reset any previous test payments for clean partial balance test
        db.query(Payment).filter(Payment.invoice_id == inv.id, Payment.payment_reference.like("PAY-2026-%")).delete()
        # Reset original payment to SCHEDULED
        for p in inv.payments:
            p.status = "SCHEDULED"
            p.payment_date = None
        db.commit()
        total_inv_amount = Decimal(str(inv.total_amount or "50000.00"))

        # 1. Check initial balance
        res_bal = client.get(f"/api/v1/payments/invoice/{inv.id}/balance")
        assert res_bal.status_code == 200
        bal_data = res_bal.json()
        assert Decimal(str(bal_data["total_invoiced_amount"])) == total_inv_amount

        # 2. Prepare partial payment of 50%
        partial_amount = (total_inv_amount / Decimal("2.00")).quantize(Decimal("0.01"))
        res_prep = client.post(
            "/api/v1/payments/prepare",
            json={
                "invoice_id": inv.id,
                "amount": float(partial_amount),
                "scheduled_date": str(date.today()),
                "payment_method": "ACH",
                "comments": "Partial disbursement 1",
            },
        )
        assert res_prep.status_code == 200
        prep_data = res_prep.json()
        payment_id = prep_data["payment_id"]
        assert prep_data["status"] == "SCHEDULED"

        # 3. Simulate settlement of partial payment
        res_sim = client.post(f"/api/v1/payments/{payment_id}/simulate")
        assert res_sim.status_code == 200
        assert res_sim.json()["status"] == "COMPLETED"

        # Re-check balance: outstanding should be reduced
        res_bal_after = client.get(f"/api/v1/payments/invoice/{inv.id}/balance")
        bal_after = res_bal_after.json()
        assert Decimal(str(bal_after["total_paid_amount"])) >= partial_amount

        # 4. Attempting to pay an amount exceeding outstanding balance must fail with 400
        res_excess = client.post(
            "/api/v1/payments/prepare",
            json={
                "invoice_id": inv.id,
                "amount": float(total_inv_amount + Decimal("10000.00")),
                "scheduled_date": str(date.today()),
                "payment_method": "ACH",
            },
        )
        assert res_excess.status_code == 400
        assert "exceeds" in res_excess.json()["detail"].lower()

        # 5. Prevent duplicate execution of an already settled payment
        res_dup_sim = client.post(f"/api/v1/payments/{payment_id}/simulate")
        assert res_dup_sim.status_code == 400
        assert "already been settled" in res_dup_sim.json()["detail"].lower()
    finally:
        db.close()


# -------------------------------------------------------------
# 4. General Ledger, Chart of Accounts, and Trial Balance API Tests
# -------------------------------------------------------------
def test_chart_of_accounts_and_trial_balance_api():
    """Verifies that /api/v1/ledger/accounts and /api/v1/ledger/trial-balance
    return structured data with double-entry balance integrity.
    """
    # 1. Chart of Accounts
    res_acc = client.get("/api/v1/ledger/accounts")
    assert res_acc.status_code == 200
    accounts = res_acc.json()
    assert len(accounts) >= 10
    codes = [a["account_code"] for a in accounts]
    assert "1101" in codes  # Bank
    assert "1401" in codes  # CGST
    assert "2101" in codes  # AP
    assert "5001" in codes  # Office Supplies

    # 2. Account Mappings
    res_map = client.get("/api/v1/ledger/mappings")
    assert res_map.status_code == 200
    mappings = res_map.json()
    assert len(mappings) >= 6

    # 3. Trial Balance
    res_tb = client.get("/api/v1/ledger/trial-balance")
    assert res_tb.status_code == 200
    tb = res_tb.json()
    assert "total_debit" in tb
    assert "total_credit" in tb
    assert "is_balanced" in tb
    assert tb["is_balanced"] is True


def test_erp_status_and_config_api():
    """Verifies /api/v1/erp/status and /api/v1/erp/config endpoints."""
    res_status = client.get("/api/v1/erp/status")
    assert res_status.status_code == 200
    st = res_status.json()
    assert st["adapter_name"] == "MOCK_UNIVERSITY_ERP"
    assert st["is_connected"] is True
    assert "mock" in st["notice"].lower()

    res_cfg = client.get("/api/v1/erp/config")
    assert res_cfg.status_code == 200
    cfg = res_cfg.json()
    assert cfg["active_adapter"] == "MOCK_UNIVERSITY_ERP"
    adapter_ids = [a["id"] for a in cfg["available_adapters"]]
    assert "MOCK_UNIVERSITY_ERP" in adapter_ids
    assert "SAP" in adapter_ids
    assert "ORACLE" in adapter_ids
