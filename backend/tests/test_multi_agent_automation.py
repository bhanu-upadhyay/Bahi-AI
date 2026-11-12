from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.invoice import Invoice
from app.models.purchase_order import PurchaseOrder
from app.models.vendor import Vendor
from app.models.agent_execution_log import AgentExecutionLog
from app.services.agents.invoice_understanding_agent import InvoiceUnderstandingAgent
from app.services.agents.vendor_verification_agent import VendorVerificationAgent
from app.services.agents.matching_agent import ThreeWayMatchingAgent
from app.services.agents.fraud_risk_agent import FraudRiskAgent
from app.services.agents.approval_recommendation_agent import ApprovalRecommendationAgent
from app.services.agents.orchestrator import AgentOrchestrator

client = TestClient(app)


def test_invoice_understanding_agent_clean_reconciliation():
    agent = InvoiceUnderstandingAgent()
    inv = Invoice(
        id=99901,
        invoice_number="INV-TEST-001",
        invoice_date="2026-11-10",
        due_date="2026-12-10",
        subtotal=Decimal("10000.00"),
        tax_amount=Decimal("1800.00"),
        total_amount=Decimal("11800.00"),
        currency="INR",
        confidence_score=Decimal("95.00"),
        extraction_metadata={
            "gst_breakdown": {
                "taxable_subtotal": "10000.00",
                "cgst_amount": "900.00",
                "sgst_amount": "900.00",
                "total_tax": "1800.00",
                "grand_total": "11800.00",
            }
        },
    )
    result = agent.execute(inv)
    assert result.status == "PASSED"
    assert result.confidence_score == Decimal("95.00")
    assert result.math_reconciled is True
    assert "INTRA_STATE_GST" in result.tax_type
    assert result.discrepancy_amount == Decimal("0.00")
    assert len(result.missing_fields) == 0


def test_invoice_understanding_agent_math_variance_and_missing_fields():
    agent = InvoiceUnderstandingAgent()
    # Discrepancy: subtotal 10000 + tax 1800 = 11800, but total is 15000 (diff = 3200)
    # Also missing invoice_number and invoice_date
    inv = Invoice(
        id=99902,
        invoice_number=None,
        invoice_date=None,
        due_date=None,
        subtotal=Decimal("10000.00"),
        tax_amount=Decimal("1800.00"),
        total_amount=Decimal("15000.00"),
        currency="INR",
        confidence_score=Decimal("40.00"),
        extraction_metadata={},
    )
    result = agent.execute(inv)
    assert result.status in ["WARNING", "FAILED"]
    assert result.math_reconciled is False
    assert result.discrepancy_amount == Decimal("3200.00")
    assert "invoice_number" in result.missing_fields
    assert "invoice_date" in result.missing_fields


def test_vendor_verification_agent_registered_and_unknown():
    db = SessionLocal()
    try:
        agent = VendorVerificationAgent()

        # Existing registered vendor (Vendor ID 1: Apex Computing Solutions)
        registered_vendor = db.query(Vendor).filter(Vendor.id == 1).first()
        assert registered_vendor is not None

        # Scenario A: Known registered vendor with matching GSTIN
        inv_known = Invoice(
            id=99903,
            vendor_id=registered_vendor.id,
            tax_identifier=registered_vendor.tax_identifier,
            extraction_metadata={"gst_breakdown": {"supplier_gstin": registered_vendor.tax_identifier}},
        )
        res_known = agent.execute(inv_known, db)
        assert res_known.status == "VERIFIED"
        assert res_known.vendor_id == registered_vendor.id
        assert res_known.legal_name == registered_vendor.legal_name
        assert res_known.gstin_matched is True
        assert res_known.is_active is True

        # Scenario B: Unknown / unassigned vendor
        inv_unknown = Invoice(
            id=99904,
            vendor_id=None,
            tax_identifier="99ABCDE1234F1Z5",
            extraction_metadata={"gst_breakdown": {"supplier_name": "Unregistered Vendor Corp"}},
        )
        res_unknown = agent.execute(inv_unknown, db)
        assert res_unknown.status == "UNKNOWN_VENDOR"
        assert res_unknown.vendor_id is None
        assert res_unknown.gstin_matched is False

        # Scenario C: Vendor assigned but GSTIN mismatch
        inv_mismatch = Invoice(
            id=99905,
            vendor_id=registered_vendor.id,
            tax_identifier="07DIFFERENT0000Z1",
            extraction_metadata={"gst_breakdown": {"supplier_gstin": "07DIFFERENT0000Z1"}},
        )
        res_mismatch = agent.execute(inv_mismatch, db)
        assert res_mismatch.status == "GSTIN_MISMATCH"
        assert res_mismatch.gstin_matched is False
    finally:
        db.close()


def test_three_way_matching_agent_full_match_and_no_po():
    db = SessionLocal()
    try:
        matching_agent = ThreeWayMatchingAgent()

        # Fetch invoice 2 which is linked to a PO
        inv2 = db.query(Invoice).filter(Invoice.id == 2).first()
        assert inv2 is not None
        assert inv2.purchase_order is not None

        res_matched = matching_agent.execute(inv2, db)
        assert res_matched.match_status == "FULL_MATCH"
        assert res_matched.po_number == inv2.purchase_order.po_number
        assert len(res_matched.grn_numbers) > 0
        assert res_matched.total_variance == Decimal("0.00")
        assert len(res_matched.line_matches) > 0

        # Scenario: Invoice without PO (Direct spend)
        inv_no_po = Invoice(
            id=99906,
            invoice_number="INV-NOPO-1",
            purchase_order_id=None,
            total_amount=Decimal("5000.00"),
        )
        res_no_po = matching_agent.execute(inv_no_po, db)
        assert res_no_po.match_status == "NO_PO"
        assert res_no_po.po_number is None
        assert "direct spend" in res_no_po.summary.lower()
    finally:
        db.close()


def test_fraud_risk_agent_scoring():
    db = SessionLocal()
    try:
        agent = FraudRiskAgent()
        understanding_agent = InvoiceUnderstandingAgent()
        vendor_agent = VendorVerificationAgent()
        matching_agent = ThreeWayMatchingAgent()

        # Invoice 2 is legitimate and matched
        inv2 = db.query(Invoice).filter(Invoice.id == 2).first()
        und2 = understanding_agent.execute(inv2)
        v2 = vendor_agent.execute(inv2, db)
        m2 = matching_agent.execute(inv2, db)

        risk2 = agent.execute(inv2, db, und2, v2, m2)
        assert risk2.risk_category in ["LOW", "MEDIUM"]
        assert risk2.risk_score < Decimal("50.00")
        assert "proceed" in risk2.recommended_action.lower() or "standard" in risk2.recommended_action.lower()

        # High risk invoice: Unknown vendor, no PO, large amount, no hash
        inv_suspicious = Invoice(
            id=99907,
            invoice_number="INV-SUSP-1",
            vendor_id=None,
            purchase_order_id=None,
            file_hash="fake_hash_12345",
            total_amount=Decimal("999999.00"),
            extraction_metadata={},
        )
        und_s = understanding_agent.execute(inv_suspicious)
        v_s = vendor_agent.execute(inv_suspicious, db)
        m_s = matching_agent.execute(inv_suspicious, db)

        risk_s = agent.execute(inv_suspicious, db, und_s, v_s, m_s)
        assert risk_s.risk_score >= Decimal("50.00")
        assert risk_s.risk_category in ["HIGH", "CRITICAL"]
        assert len(risk_s.risk_factors) >= 2
    finally:
        db.close()


def test_approval_recommendation_agent_decision_rules():
    agent = ApprovalRecommendationAgent()
    inv = Invoice(id=1, invoice_number="INV-TEST", total_amount=Decimal("1000.00"))

    # Case 1: All clean -> APPROVE
    from app.schemas.agent import (
        InvoiceUnderstandingResult,
        VendorVerificationResult,
        ThreeWayMatchingResult,
        FraudRiskResult,
    )

    und_pass = InvoiceUnderstandingResult(
        status="PASSED",
        confidence_score=Decimal("95.00"),
        tax_type="INTRA_STATE_GST",
        math_reconciled=True,
        summary="Clean",
    )
    v_pass = VendorVerificationResult(
        status="VERIFIED",
        gstin_matched=True,
        is_active=True,
        has_bank_details=True,
        summary="Verified",
    )
    m_pass = ThreeWayMatchingResult(
        match_status="FULL_MATCH",
        total_variance=Decimal("0.00"),
        summary="Full match",
    )
    f_low = FraudRiskResult(
        risk_score=Decimal("10.00"),
        risk_category="LOW",
        recommended_action="PROCEED_NORMAL_APPROVAL",
        summary="Low risk",
    )

    rec_approve = agent.execute(inv, und_pass, v_pass, m_pass, f_low)
    assert rec_approve.recommendation == "APPROVE"
    assert len(rec_approve.action_checklist) > 0
    assert len(rec_approve.unresolved_issues) == 0

    # Case 2: High Risk / Duplicate -> REJECT
    f_crit = FraudRiskResult(
        risk_score=Decimal("85.00"),
        risk_category="CRITICAL",
        recommended_action="REJECT_AND_FLAG_FRAUD",
        summary="Critical risk",
    )
    rec_reject = agent.execute(inv, und_pass, v_pass, m_pass, f_crit)
    assert rec_reject.recommendation == "REJECT"
    assert len(rec_reject.unresolved_issues) > 0

    # Case 3: Price Variance / Minor issues -> REVIEW
    m_var = ThreeWayMatchingResult(
        match_status="PRICE_VARIANCE",
        total_variance=Decimal("250.00"),
        summary="Price variance detected",
        discrepancies=["Item 1 unit price higher by Rs 250"],
    )
    rec_review = agent.execute(inv, und_pass, v_pass, m_var, f_low)
    assert rec_review.recommendation == "REVIEW"


def test_agent_orchestrator_pipeline_and_idempotency():
    db = SessionLocal()
    try:
        orchestrator = AgentOrchestrator()

        # Invoice 2
        inv_id = 2
        inv_before = db.query(Invoice).filter(Invoice.id == inv_id).first()
        initial_approval_status = inv_before.approval_status

        report1 = orchestrator.analyze_invoice(inv_id, db)
        assert report1.invoice_id == inv_id
        assert report1.orchestrator_status == "COMPLETED"
        assert report1.recommendation in ["APPROVE", "REVIEW", "REJECT"]
        assert report1.understanding is not None
        assert report1.vendor_verification is not None
        assert report1.matching is not None
        assert report1.fraud_risk is not None
        assert report1.approval_recommendation is not None
        assert len(report1.execution_logs) >= 5

        # Check logs recorded in DB
        logs = db.query(AgentExecutionLog).filter(AgentExecutionLog.invoice_id == inv_id).all()
        assert len(logs) >= 5

        # Verify Invoice status and approval isolation:
        # Approval status must remain under strict human control, untouched by agents
        inv_db = db.query(Invoice).filter(Invoice.id == inv_id).first()
        assert inv_db.approval_status == initial_approval_status
        assert inv_db.processing_status in ["MATCHED", "EXCEPTION", "VALIDATED"]
        assert "agent_analysis" in inv_db.extraction_metadata

        # Idempotency / Retry test
        report2 = orchestrator.analyze_invoice(inv_id, db)
        assert report2.invoice_id == inv_id
        assert report2.orchestrator_status == "COMPLETED"
    finally:
        db.close()


def test_multi_agent_api_endpoints():
    # 1. POST /api/v1/agents/analyze/{invoice_id}
    res_analyze = client.post("/api/v1/agents/analyze/2")
    assert res_analyze.status_code == 200
    data = res_analyze.json()
    assert data["invoice_id"] == 2
    assert "orchestrator_status" in data
    assert "recommendation" in data
    assert "risk_score" in data
    assert "understanding" in data
    assert "vendor_verification" in data
    assert "matching" in data
    assert "fraud_risk" in data
    assert "approval_recommendation" in data

    # 2. GET /api/v1/agents/analysis/{invoice_id}
    res_get = client.get("/api/v1/agents/analysis/2")
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["invoice_id"] == 2
    assert get_data["recommendation"] == data["recommendation"]

    # 3. GET /api/v1/agents/logs/{invoice_id}
    res_logs = client.get("/api/v1/agents/logs/2")
    assert res_logs.status_code == 200
    logs = res_logs.json()
    assert len(logs) >= 5
    agent_names = [log["agent_name"] for log in logs]
    assert "InvoiceUnderstandingAgent" in agent_names
    assert "VendorVerificationAgent" in agent_names
    assert "ThreeWayMatchingAgent" in agent_names
    assert "FraudRiskAgent" in agent_names
    assert "ApprovalRecommendationAgent" in agent_names

    # 4. POST /api/v1/agents/retry/{invoice_id}
    res_retry = client.post("/api/v1/agents/retry/2")
    assert res_retry.status_code == 200
    retry_data = res_retry.json()
    assert retry_data["invoice_id"] == 2

    # 5. Convenience endpoints under /invoices/{id}/
    res_inv_analyze = client.post("/api/v1/invoices/2/analyze")
    assert res_inv_analyze.status_code == 200

    res_inv_analysis = client.get("/api/v1/invoices/2/analysis")
    assert res_inv_analysis.status_code == 200

    res_inv_logs = client.get("/api/v1/invoices/2/agent-logs")
    assert res_inv_logs.status_code == 200

    # 6. Non-existent invoice 404 test
    res_404 = client.post("/api/v1/agents/analyze/999999")
    assert res_404.status_code == 404
