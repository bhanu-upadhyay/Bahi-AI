"""
Comprehensive Financial Calculations and Reconciliation Test Suite for Bahi-AI.

Validates accounts payable financial rules:
1. Full PO delivery and full invoice.
2. Partial delivery with invoice quantity equal to GRN accepted quantity (Zero monetary variance).
3. Invoice quantity exceeding accepted GRN quantity (Quantity variance detected).
4. Invoice quantity below accepted GRN quantity (Supported partial invoicing).
5. PO price variance (Unit rate discrepancy detected).
6. Quantity overbilling (Billed quantity exceeds warehouse receipt).
7. Tax calculation, asymmetry, and double taxation detection.
8. Incorrect invoice grand total (Subtotal + Tax != Total).
9. Duplicate invoice submission (CRITICAL risk score).
10. Multiple invoice lines with different tax rates.
"""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceLine
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.goods_receipt import GoodsReceipt, GoodsReceiptLine
from app.models.vendor import Vendor
from app.models.department import Department
from app.models.user import User
from app.services.agents.matching_agent import ThreeWayMatchingAgent
from app.services.agents.invoice_understanding_agent import InvoiceUnderstandingAgent
from app.services.agents.fraud_risk_agent import FraudRiskAgent


@pytest.fixture
def base_entities(db_session: Session):
    """Sets up isolated Vendor, Department, and User fixtures within the rollback transaction."""
    dept = db_session.query(Department).first()
    if not dept:
        dept = Department(name="Computer Science & Engineering", code="CSE", description="CSE Dept")
        db_session.add(dept)
        db_session.flush()

    user = db_session.query(User).first()
    if not user:
        user = User(
            full_name="Prof. Test User",
            email="test.user@jklu.edu.in",
            password_hash="fakehash",
            role="FINANCE_OFFICER",
            department_id=dept.id,
        )
        db_session.add(user)
        db_session.flush()

    vendor = db_session.query(Vendor).first()
    if not vendor:
        vendor = Vendor(
            name="Rajasthan Tech & Lab Innovations Pvt Ltd",
            vendor_code="VND-RAJ-01",
            tax_identifier="08AAACR5678E1Z2",
            is_active=True,
        )
        db_session.add(vendor)
        db_session.flush()

    return {"department": dept, "vendor": vendor, "user": user}


# -----------------------------------------------------------------------------
# 1. Full PO Delivery and Full Invoice
# -----------------------------------------------------------------------------

def test_full_po_delivery_and_full_invoice(db_session: Session, base_entities):
    """Verify that when 100% of order is delivered, accepted, and invoiced, match is FULL_MATCH with 0 variance."""
    dept = base_entities["department"]
    vendor = base_entities["vendor"]
    user = base_entities["user"]

    # 10 units @ 1000 = 10000 + 18% tax (1800) = 11800
    po = PurchaseOrder(
        po_number="PO-TEST-FULL-01",
        vendor_id=vendor.id,
        department_id=dept.id,
        issue_date=date(2026, 11, 1),
        created_by=user.id,
        total_amount=Decimal("11800.00"),
        tax_amount=Decimal("1800.00"),
        status="DELIVERED",
    )
    db_session.add(po)
    db_session.flush()

    pol = PurchaseOrderLine(
        purchase_order_id=po.id,
        line_number=1,
        item_description="Precision Lab Sensor",
        quantity=Decimal("10.00"),
        unit_price=Decimal("1000.00"),
        tax_rate=Decimal("18.00"),
        total_amount=Decimal("11800.00"),
    )
    db_session.add(pol)
    db_session.flush()

    grn = GoodsReceipt(
        grn_number="GRN-TEST-FULL-01",
        purchase_order_id=po.id,
        received_by=user.id,
        received_date=date(2026, 11, 3),
        status="COMPLETED",
    )
    db_session.add(grn)
    db_session.flush()

    grnl = GoodsReceiptLine(
        goods_receipt_id=grn.id,
        purchase_order_line_id=pol.id,
        quantity_ordered=Decimal("10.00"),
        quantity_received=Decimal("10.00"),
        quantity_accepted=Decimal("10.00"),
        quantity_rejected=Decimal("0.00"),
    )
    db_session.add(grnl)
    db_session.flush()

    inv = Invoice(
        invoice_number="INV-TEST-FULL-01",
        normalized_invoice_number="INVTESTFULL01",
        vendor_id=vendor.id,
        purchase_order_id=po.id,
        department_id=dept.id,
        subtotal=Decimal("10000.00"),
        tax_amount=Decimal("1800.00"),
        total_amount=Decimal("11800.00"),
    )
    db_session.add(inv)
    db_session.flush()

    inv_l = InvoiceLine(
        invoice_id=inv.id,
        line_number=1,
        description="Precision Lab Sensor",
        quantity=Decimal("10.00"),
        unit_price=Decimal("1000.00"),
        tax_rate=Decimal("18.00"),
        line_total=Decimal("11800.00"),
    )
    db_session.add(inv_l)
    db_session.flush()

    agent = ThreeWayMatchingAgent()
    result = agent.execute(inv, db_session)

    assert result.match_status == "FULL_MATCH"
    assert result.total_variance == Decimal("0.00")
    assert len(result.discrepancies) == 0
    assert len(result.line_matches) == 1
    assert result.line_matches[0].price_variance == Decimal("0.00")
    assert result.line_matches[0].quantity_variance == Decimal("0.00")


# -----------------------------------------------------------------------------
# 2. Partial Delivery with Invoiced Qty Equal to GRN Accepted Qty (Observed Scenario)
# -----------------------------------------------------------------------------

def test_partial_delivery_invoiced_qty_equals_grn_accepted_qty(db_session: Session, base_entities):
    """
    CRITICAL AUDIT FIX:
    PO ordered 40 units (₹198,240).
    Supplier delivered 20 units (GRN accepted = 20).
    Invoice bills strictly for 20 units @ PO rate (₹99,120).
    
    The outstanding unfulfilled 20 units on the PO MUST NOT be reported as a ₹99,120 variance.
    Total variance MUST be ₹0.00, and match status must be PARTIAL_MATCH.
    """
    dept = base_entities["department"]
    vendor = base_entities["vendor"]
    user = base_entities["user"]

    po = PurchaseOrder(
        po_number="PO-TEST-PARTIAL-02",
        vendor_id=vendor.id,
        department_id=dept.id,
        issue_date=date(2026, 11, 1),
        created_by=user.id,
        total_amount=Decimal("198240.00"),
        tax_amount=Decimal("30240.00"),
        status="PARTIAL",
    )
    db_session.add(po)
    db_session.flush()

    pol = PurchaseOrderLine(
        purchase_order_id=po.id,
        line_number=1,
        item_description="Ergonomic Mechanical Keyboards",
        quantity=Decimal("40.00"),
        unit_price=Decimal("4200.00"),
        tax_rate=Decimal("18.00"),
        total_amount=Decimal("198240.00"),
    )
    db_session.add(pol)
    db_session.flush()

    grn = GoodsReceipt(
        grn_number="GRN-TEST-PARTIAL-02",
        purchase_order_id=po.id,
        received_by=user.id,
        received_date=date(2026, 11, 4),
        status="PARTIAL",
    )
    db_session.add(grn)
    db_session.flush()

    grnl = GoodsReceiptLine(
        goods_receipt_id=grn.id,
        purchase_order_line_id=pol.id,
        quantity_ordered=Decimal("40.00"),
        quantity_received=Decimal("20.00"),
        quantity_accepted=Decimal("20.00"),
        quantity_rejected=Decimal("0.00"),
    )
    db_session.add(grnl)
    db_session.flush()

    # Invoice strictly bills for the 20 accepted units: 20 * 4200 = 84000 + 15120 tax = 99120
    inv = Invoice(
        invoice_number="INV-TEST-PARTIAL-02",
        normalized_invoice_number="INVTESTPARTIAL02",
        vendor_id=vendor.id,
        purchase_order_id=po.id,
        department_id=dept.id,
        subtotal=Decimal("84000.00"),
        tax_amount=Decimal("15120.00"),
        total_amount=Decimal("99120.00"),
    )
    db_session.add(inv)
    db_session.flush()

    inv_l = InvoiceLine(
        invoice_id=inv.id,
        line_number=1,
        description="Ergonomic Mechanical Keyboards",
        quantity=Decimal("20.00"),
        unit_price=Decimal("4200.00"),
        tax_rate=Decimal("18.00"),
        line_total=Decimal("99120.00"),
    )
    db_session.add(inv_l)
    db_session.flush()

    agent = ThreeWayMatchingAgent()
    result = agent.execute(inv, db_session)

    # Assert correct financial reconciliation
    assert result.match_status == "PARTIAL_MATCH"
    assert result.total_variance == Decimal("0.00"), (
        f"Incorrect total variance! Expected ₹0.00, got: {result.total_variance}"
    )
    assert len(result.discrepancies) == 0
    assert result.line_matches[0].price_variance == Decimal("0.00")
    assert result.line_matches[0].quantity_variance == Decimal("0.00")
    assert result.line_matches[0].po_quantity == Decimal("40.00")
    assert result.line_matches[0].grn_accepted_quantity == Decimal("20.00")
    assert result.line_matches[0].invoice_quantity == Decimal("20.00")


# -----------------------------------------------------------------------------
# 3. Invoice Quantity Exceeding Accepted GRN Quantity
# -----------------------------------------------------------------------------

def test_invoice_quantity_exceeding_accepted_grn_quantity(db_session: Session, base_entities):
    """
    Vendor bills for 25 units when only 20 were accepted by warehouse.
    5 units are overbilled.
    Monetary discrepancy: 5 units * 1000 + 18% tax = 5900.00.
    """
    dept = base_entities["department"]
    vendor = base_entities["vendor"]
    user = base_entities["user"]

    po = PurchaseOrder(
        po_number="PO-TEST-OVER-03", vendor_id=vendor.id, department_id=dept.id,
        issue_date=date(2026, 11, 1), created_by=user.id, total_amount=Decimal("47200.00")
    )
    db_session.add(po)
    db_session.flush()

    pol = PurchaseOrderLine(
        purchase_order_id=po.id, line_number=1, item_description="Workbench Cables",
        quantity=Decimal("40.00"), unit_price=Decimal("1000.00"), tax_rate=Decimal("18.00"), total_amount=Decimal("47200.00")
    )
    db_session.add(pol)
    db_session.flush()

    grn = GoodsReceipt(
        grn_number="GRN-TEST-OVER-03", purchase_order_id=po.id, received_by=user.id,
        received_date=date(2026, 11, 3), status="PARTIAL"
    )
    db_session.add(grn)
    db_session.flush()

    grnl = GoodsReceiptLine(
        goods_receipt_id=grn.id, purchase_order_line_id=pol.id,
        quantity_ordered=Decimal("40.00"), quantity_received=Decimal("20.00"), quantity_accepted=Decimal("20.00")
    )
    db_session.add(grnl)
    db_session.flush()

    # Invoiced for 25 units (5 overbilled)
    inv = Invoice(
        invoice_number="INV-TEST-OVER-03", normalized_invoice_number="INVTESTOVER03",
        vendor_id=vendor.id, purchase_order_id=po.id, department_id=dept.id,
        subtotal=Decimal("25000.00"), tax_amount=Decimal("4500.00"), total_amount=Decimal("29500.00")
    )
    db_session.add(inv)
    db_session.flush()

    inv_l = InvoiceLine(
        invoice_id=inv.id, line_number=1, description="Workbench Cables",
        quantity=Decimal("25.00"), unit_price=Decimal("1000.00"), tax_rate=Decimal("18.00"), line_total=Decimal("29500.00")
    )
    db_session.add(inv_l)
    db_session.flush()

    agent = ThreeWayMatchingAgent()
    result = agent.execute(inv, db_session)

    assert result.match_status == "QUANTITY_VARIANCE"
    # Overbilled 5 units: 5 * 1000 * 1.18 = 5900.00
    assert result.total_variance == Decimal("5900.00")
    assert result.line_matches[0].quantity_variance == Decimal("5.00")
    assert result.line_matches[0].price_variance == Decimal("0.00")


# -----------------------------------------------------------------------------
# 4. Invoice Quantity Below Accepted GRN Quantity
# -----------------------------------------------------------------------------

def test_invoice_quantity_below_accepted_grn_quantity(db_session: Session, base_entities):
    """
    Warehouse accepted 30 units, but invoice bills for only 20 units (progressive billing).
    Invoiced quantity is fully supported by receipts. Monetary discrepancy is 0.
    """
    dept = base_entities["department"]
    vendor = base_entities["vendor"]
    user = base_entities["user"]

    po = PurchaseOrder(
        po_number="PO-TEST-BELOW-04", vendor_id=vendor.id, department_id=dept.id,
        issue_date=date(2026, 11, 1), created_by=user.id, total_amount=Decimal("59000.00")
    )
    db_session.add(po)
    db_session.flush()

    pol = PurchaseOrderLine(
        purchase_order_id=po.id, line_number=1, item_description="Optical Mice",
        quantity=Decimal("50.00"), unit_price=Decimal("1000.00"), tax_rate=Decimal("18.00"), total_amount=Decimal("59000.00")
    )
    db_session.add(pol)
    db_session.flush()

    grn = GoodsReceipt(
        grn_number="GRN-TEST-BELOW-04", purchase_order_id=po.id, received_by=user.id,
        received_date=date(2026, 11, 3), status="PARTIAL"
    )
    db_session.add(grn)
    db_session.flush()

    grnl = GoodsReceiptLine(
        goods_receipt_id=grn.id, purchase_order_line_id=pol.id,
        quantity_ordered=Decimal("50.00"), quantity_received=Decimal("30.00"), quantity_accepted=Decimal("30.00")
    )
    db_session.add(grnl)
    db_session.flush()

    # Invoice bills for 20 units (supported by the 30 accepted)
    inv = Invoice(
        invoice_number="INV-TEST-BELOW-04", normalized_invoice_number="INVTESTBELOW04",
        vendor_id=vendor.id, purchase_order_id=po.id, department_id=dept.id,
        subtotal=Decimal("20000.00"), tax_amount=Decimal("3600.00"), total_amount=Decimal("23600.00")
    )
    db_session.add(inv)
    db_session.flush()

    inv_l = InvoiceLine(
        invoice_id=inv.id, line_number=1, description="Optical Mice",
        quantity=Decimal("20.00"), unit_price=Decimal("1000.00"), tax_rate=Decimal("18.00"), line_total=Decimal("23600.00")
    )
    db_session.add(inv_l)
    db_session.flush()

    agent = ThreeWayMatchingAgent()
    result = agent.execute(inv, db_session)

    assert result.match_status == "PARTIAL_MATCH"
    assert result.total_variance == Decimal("0.00")
    assert result.line_matches[0].quantity_variance == Decimal("-10.00")


# -----------------------------------------------------------------------------
# 5. PO Price Variance
# -----------------------------------------------------------------------------

def test_po_price_variance(db_session: Session, base_entities):
    """
    PO authorized unit price is ₹1,000, but supplier billed at ₹1,200 (+₹200 variance).
    10 units * ₹200 = ₹2,000 + 18% GST (₹360) = ₹2,360 total variance.
    """
    dept = base_entities["department"]
    vendor = base_entities["vendor"]
    user = base_entities["user"]

    po = PurchaseOrder(
        po_number="PO-TEST-PVAR-05", vendor_id=vendor.id, department_id=dept.id,
        issue_date=date(2026, 11, 1), created_by=user.id, total_amount=Decimal("11800.00")
    )
    db_session.add(po)
    db_session.flush()

    pol = PurchaseOrderLine(
        purchase_order_id=po.id, line_number=1, item_description="Lab Adapters",
        quantity=Decimal("10.00"), unit_price=Decimal("1000.00"), tax_rate=Decimal("18.00"), total_amount=Decimal("11800.00")
    )
    db_session.add(pol)
    db_session.flush()

    grn = GoodsReceipt(
        grn_number="GRN-TEST-PVAR-05", purchase_order_id=po.id, received_by=user.id,
        received_date=date(2026, 11, 3), status="COMPLETED"
    )
    db_session.add(grn)
    db_session.flush()

    grnl = GoodsReceiptLine(
        goods_receipt_id=grn.id, purchase_order_line_id=pol.id,
        quantity_ordered=Decimal("10.00"), quantity_received=Decimal("10.00"), quantity_accepted=Decimal("10.00")
    )
    db_session.add(grnl)
    db_session.flush()

    # Billed at 1200 instead of 1000
    inv = Invoice(
        invoice_number="INV-TEST-PVAR-05", normalized_invoice_number="INVTESTPVAR05",
        vendor_id=vendor.id, purchase_order_id=po.id, department_id=dept.id,
        subtotal=Decimal("12000.00"), tax_amount=Decimal("2160.00"), total_amount=Decimal("14160.00")
    )
    db_session.add(inv)
    db_session.flush()

    inv_l = InvoiceLine(
        invoice_id=inv.id, line_number=1, description="Lab Adapters",
        quantity=Decimal("10.00"), unit_price=Decimal("1200.00"), tax_rate=Decimal("18.00"), line_total=Decimal("14160.00")
    )
    db_session.add(inv_l)
    db_session.flush()

    agent = ThreeWayMatchingAgent()
    result = agent.execute(inv, db_session)

    assert result.match_status == "PRICE_VARIANCE"
    assert result.line_matches[0].price_variance == Decimal("200.00")
    assert result.total_variance == Decimal("2360.00")


# -----------------------------------------------------------------------------
# 6. Quantity Overbilling
# -----------------------------------------------------------------------------

def test_quantity_overbilling(db_session: Session, base_entities):
    """
    PO ordered 10 units @ 5,000.
    Warehouse received and accepted 10 units.
    Invoice bills for 12 units (+2 overbilled).
    Monetary discrepancy: 2 * 5000 * 1.18 = 11,800.00.
    """
    dept = base_entities["department"]
    vendor = base_entities["vendor"]
    user = base_entities["user"]

    po = PurchaseOrder(
        po_number="PO-TEST-QOVER-06", vendor_id=vendor.id, department_id=dept.id,
        issue_date=date(2026, 11, 1), created_by=user.id, total_amount=Decimal("59000.00")
    )
    db_session.add(po)
    db_session.flush()

    pol = PurchaseOrderLine(
        purchase_order_id=po.id, line_number=1, item_description="Server Rack Shelves",
        quantity=Decimal("10.00"), unit_price=Decimal("5000.00"), tax_rate=Decimal("18.00"), total_amount=Decimal("59000.00")
    )
    db_session.add(pol)
    db_session.flush()

    grn = GoodsReceipt(
        grn_number="GRN-TEST-QOVER-06", purchase_order_id=po.id, received_by=user.id,
        received_date=date(2026, 11, 3), status="COMPLETED"
    )
    db_session.add(grn)
    db_session.flush()

    grnl = GoodsReceiptLine(
        goods_receipt_id=grn.id, purchase_order_line_id=pol.id,
        quantity_ordered=Decimal("10.00"), quantity_received=Decimal("10.00"), quantity_accepted=Decimal("10.00")
    )
    db_session.add(grnl)
    db_session.flush()

    inv = Invoice(
        invoice_number="INV-TEST-QOVER-06", normalized_invoice_number="INVTESTQOVER06",
        vendor_id=vendor.id, purchase_order_id=po.id, department_id=dept.id,
        subtotal=Decimal("60000.00"), tax_amount=Decimal("10800.00"), total_amount=Decimal("70800.00")
    )
    db_session.add(inv)
    db_session.flush()

    inv_l = InvoiceLine(
        invoice_id=inv.id, line_number=1, description="Server Rack Shelves",
        quantity=Decimal("12.00"), unit_price=Decimal("5000.00"), tax_rate=Decimal("18.00"), line_total=Decimal("70800.00")
    )
    db_session.add(inv_l)
    db_session.flush()

    agent = ThreeWayMatchingAgent()
    result = agent.execute(inv, db_session)

    assert result.match_status == "QUANTITY_VARIANCE"
    assert result.total_variance == Decimal("11800.00")
    assert result.line_matches[0].quantity_variance == Decimal("2.00")


# -----------------------------------------------------------------------------
# 7. Tax Calculation and Double Taxation Detection
# -----------------------------------------------------------------------------

def test_tax_calculation_and_double_taxation():
    """
    Verify that an invoice illegally charging both Inter-state IGST and Intra-state CGST/SGST
    is flagged for double taxation violation and math reconciliation failure.
    """
    agent = InvoiceUnderstandingAgent()

    inv_double_tax = Invoice(
        invoice_number="INV-TEST-TAX-07",
        subtotal=Decimal("10000.00"),
        tax_amount=Decimal("3600.00"),
        total_amount=Decimal("13600.00"),
        extraction_metadata={
            "gst_breakdown": {
                "cgst_amount": "900.00",
                "sgst_amount": "900.00",
                "igst_amount": "1800.00",  # Illegal simultaneous IGST
            }
        },
    )

    result = agent.execute(inv_double_tax)
    assert not result.math_reconciled
    assert "CONFLICT_DOUBLE_TAXATION" in result.tax_type
    assert any("double taxation" in abn.lower() for abn in result.abnormalities)


# -----------------------------------------------------------------------------
# 8. Incorrect Invoice Grand Total (Subtotal + Tax != Total)
# -----------------------------------------------------------------------------

def test_incorrect_invoice_grand_total(db_session: Session):
    """
    Subtotal is ₹10,000, Tax is ₹1,800. Expected total is ₹11,800.
    Invoice displays ₹13,000 (₹1,200 clerical or fraudulent discrepancy).
    """
    agent = InvoiceUnderstandingAgent()

    inv_math_err = Invoice(
        invoice_number="INV-TEST-MATH-08",
        subtotal=Decimal("10000.00"),
        tax_amount=Decimal("1800.00"),
        total_amount=Decimal("13000.00"),  # 1200 discrepancy
    )

    result = agent.execute(inv_math_err)
    assert not result.math_reconciled
    assert result.discrepancy_amount == Decimal("1200.00")
    assert any("financial reconciliation failed" in abn.lower() for abn in result.abnormalities)

    # Check FraudRiskAgent reacts to mathematical discrepancy
    risk_agent = FraudRiskAgent()
    risk_result = risk_agent.execute(inv_math_err, db_session, understanding_res=result)
    assert any(rf.factor == "FINANCIAL_INCONSISTENCY" for rf in risk_result.risk_factors)


# -----------------------------------------------------------------------------
# 9. Duplicate Invoice Submission
# -----------------------------------------------------------------------------

def test_duplicate_invoice_submission(db_session: Session, base_entities):
    """
    Submitting an invoice with a duplicate normalized invoice number from the same vendor
    must trigger a CRITICAL duplicate fraud alert (score impact >= 75).
    """
    vendor = base_entities["vendor"]

    # Original existing recorded invoice
    inv_original = Invoice(
        invoice_number="INV-2026-DUP-MASTER",
        normalized_invoice_number="INV2026DUPMASTER",
        vendor_id=vendor.id,
        total_amount=Decimal("50000.00"),
        processing_status="MATCHED",
    )
    db_session.add(inv_original)
    db_session.flush()

    # Second submission with the same invoice number (using -DUP- suffix as in upload workflow)
    inv_duplicate = Invoice(
        invoice_number="INV-2026-DUP-MASTER",
        normalized_invoice_number="INV2026DUPMASTER-DUP-01",
        vendor_id=vendor.id,
        total_amount=Decimal("50000.00"),
    )

    risk_agent = FraudRiskAgent()
    risk_result = risk_agent.execute(inv_duplicate, db_session)

    assert risk_result.risk_category in ("HIGH", "CRITICAL")
    assert risk_result.risk_score >= Decimal("75.00")
    assert any(rf.factor == "DUPLICATE_INVOICE_NUMBER" for rf in risk_result.risk_factors)


# -----------------------------------------------------------------------------
# 10. Multiple Invoice Lines with Different Tax Rates
# -----------------------------------------------------------------------------

def test_multiple_invoice_lines_with_different_tax_rates(db_session: Session, base_entities):
    """
    Multi-line invoice with mixed tax rates:
    Line 1: 10 units @ 1000 with 18% GST (Subtotal: 10,000, Tax: 1,800, Total: 11,800)
    Line 2: 5 units @ 2000 with 12% GST (Subtotal: 10,000, Tax: 1,200, Total: 11,200)
    Grand Total: 23,000.00.

    Case A: Perfect match -> FULL_MATCH, Total variance = ₹0.00.
    Case B: Line 1 has +100 price variance -> PRICE_VARIANCE, Total variance = ₹1,180.00 (100 * 10 * 1.18).
    """
    dept = base_entities["department"]
    vendor = base_entities["vendor"]
    user = base_entities["user"]

    po = PurchaseOrder(
        po_number="PO-TEST-MULTITAX-10", vendor_id=vendor.id, department_id=dept.id,
        issue_date=date(2026, 11, 1), created_by=user.id,
        total_amount=Decimal("23000.00"), tax_amount=Decimal("3000.00")
    )
    db_session.add(po)
    db_session.flush()

    pol1 = PurchaseOrderLine(
        purchase_order_id=po.id, line_number=1, item_description="Software Licenses",
        quantity=Decimal("10.00"), unit_price=Decimal("1000.00"), tax_rate=Decimal("18.00"), total_amount=Decimal("11800.00")
    )
    pol2 = PurchaseOrderLine(
        purchase_order_id=po.id, line_number=2, item_description="Hardware Adapters",
        quantity=Decimal("5.00"), unit_price=Decimal("2000.00"), tax_rate=Decimal("12.00"), total_amount=Decimal("11200.00")
    )
    db_session.add_all([pol1, pol2])
    db_session.flush()

    grn = GoodsReceipt(
        grn_number="GRN-TEST-MULTITAX-10", purchase_order_id=po.id, received_by=user.id,
        received_date=date(2026, 11, 3), status="COMPLETED"
    )
    db_session.add(grn)
    db_session.flush()

    grnl1 = GoodsReceiptLine(
        goods_receipt_id=grn.id, purchase_order_line_id=pol1.id,
        quantity_ordered=Decimal("10.00"), quantity_received=Decimal("10.00"), quantity_accepted=Decimal("10.00")
    )
    grnl2 = GoodsReceiptLine(
        goods_receipt_id=grn.id, purchase_order_line_id=pol2.id,
        quantity_ordered=Decimal("5.00"), quantity_received=Decimal("5.00"), quantity_accepted=Decimal("5.00")
    )
    db_session.add_all([grnl1, grnl2])
    db_session.flush()

    # Case A: Exact match
    inv_matched = Invoice(
        invoice_number="INV-TEST-MULTITAX-10A", normalized_invoice_number="INVTESTMULTITAX10A",
        vendor_id=vendor.id, purchase_order_id=po.id, department_id=dept.id,
        subtotal=Decimal("20000.00"), tax_amount=Decimal("3000.00"), total_amount=Decimal("23000.00")
    )
    db_session.add(inv_matched)
    db_session.flush()

    invl1 = InvoiceLine(
        invoice_id=inv_matched.id, line_number=1, description="Software Licenses",
        quantity=Decimal("10.00"), unit_price=Decimal("1000.00"), tax_rate=Decimal("18.00"), line_total=Decimal("11800.00")
    )
    invl2 = InvoiceLine(
        invoice_id=inv_matched.id, line_number=2, description="Hardware Adapters",
        quantity=Decimal("5.00"), unit_price=Decimal("2000.00"), tax_rate=Decimal("12.00"), line_total=Decimal("11200.00")
    )
    db_session.add_all([invl1, invl2])
    db_session.flush()

    agent = ThreeWayMatchingAgent()
    res_a = agent.execute(inv_matched, db_session)
    assert res_a.match_status == "FULL_MATCH"
    assert res_a.total_variance == Decimal("0.00")

    # Case B: Line 1 has unit price of 1100 (+100 variance @ 18% tax = 1180.00)
    inv_variance = Invoice(
        invoice_number="INV-TEST-MULTITAX-10B", normalized_invoice_number="INVTESTMULTITAX10B",
        vendor_id=vendor.id, purchase_order_id=po.id, department_id=dept.id,
        subtotal=Decimal("21000.00"), tax_amount=Decimal("3180.00"), total_amount=Decimal("24180.00")
    )
    db_session.add(inv_variance)
    db_session.flush()

    invl1_var = InvoiceLine(
        invoice_id=inv_variance.id, line_number=1, description="Software Licenses",
        quantity=Decimal("10.00"), unit_price=Decimal("1100.00"), tax_rate=Decimal("18.00"), line_total=Decimal("12980.00")
    )
    invl2_var = InvoiceLine(
        invoice_id=inv_variance.id, line_number=2, description="Hardware Adapters",
        quantity=Decimal("5.00"), unit_price=Decimal("2000.00"), tax_rate=Decimal("12.00"), line_total=Decimal("11200.00")
    )
    db_session.add_all([invl1_var, invl2_var])
    db_session.flush()

    res_b = agent.execute(inv_variance, db_session)
    assert res_b.match_status == "PRICE_VARIANCE"
    # Monetary variance: 10 units * 100 * 1.18 = 1180.00
    assert res_b.total_variance == Decimal("1180.00")
    assert res_b.line_matches[0].price_variance == Decimal("100.00")
    assert res_b.line_matches[1].price_variance == Decimal("0.00")
