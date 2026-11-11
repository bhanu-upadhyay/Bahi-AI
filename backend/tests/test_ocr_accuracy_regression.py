from datetime import date
from decimal import Decimal
import io
import os
import uuid
import fitz
from PIL import Image, ImageDraw
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.services.extraction_service import (
    extract_fields_from_text,
    clean_amount,
    parse_date_string,
    extract_financial_fields,
)
from app.services.ocr_service import extract_document_text

client = TestClient(app)

SAMPLE_PDF_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "random_vendor_invoice.pdf"
)


def create_sample_pdf(text: str) -> bytes:
    """Helper to generate a valid digital PDF in-memory using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_regression_sample_gst_invoice_values():
    """REGRESSION TEST: Verifies that the exact sample GST invoice
    (random_vendor_invoice.pdf) extracts all expected fields accurately:
      - Vendor: Gupta Office Supplies
      - GSTIN: 08HWZOU5586H5Z7
      - Invoice number: 9766
      - Invoice date: 11-11-2026 (2026-11-11)
      - Customer: Agrawal Infotech
      - Purchase Order: None
      - Taxable subtotal: ₹34,300.00
      - CGST: ₹3,087.00
      - SGST: ₹3,087.00
      - Total tax: ₹6,174.00
      - Grand total: ₹40,474.00
      - Mathematical reconciliation: 34,300 + 3,087 + 3,087 = 40,474
    """
    assert os.path.exists(SAMPLE_PDF_PATH), f"Sample fixture not found at {SAMPLE_PDF_PATH}"

    # Extract text using PyMuPDF service
    raw_text, ocr_method, meta = extract_document_text(SAMPLE_PDF_PATH, "application/pdf")
    assert ocr_method == "PYMUPDF_DIGITAL"
    assert len(raw_text) > 100

    with SessionLocal() as db:
        extracted = extract_fields_from_text(raw_text, db)

    # 1. Vendor Extraction
    assert extracted["vendor_name"] == "Gupta Office Supplies", (
        f"Expected 'Gupta Office Supplies', got '{extracted['vendor_name']}'"
    )

    # 2. GSTIN Extraction
    assert extracted["tax_identifier"] == "08HWZOU5586H5Z7", (
        f"Expected supplier GSTIN '08HWZOU5586H5Z7', got '{extracted['tax_identifier']}'"
    )

    # 3. Customer Extraction
    assert extracted["customer_name"] == "Agrawal Infotech", (
        f"Expected customer 'Agrawal Infotech', got '{extracted['customer_name']}'"
    )
    assert extracted["customer_gstin"] == "08FEYMY0855T9ZT", (
        f"Expected customer GSTIN '08FEYMY0855T9ZT', got '{extracted['customer_gstin']}'"
    )

    # 4. Invoice Identifiers & Dates
    assert extracted["invoice_number"] == "9766"
    assert extracted["invoice_date"] == date(2026, 11, 11)
    assert extracted["due_date"] is None
    assert extracted["purchase_order_number"] is None

    # 5. Financial Values (Decimal Precision)
    assert extracted["subtotal"] == Decimal("34300.00"), (
        f"Expected subtotal 34300.00, got {extracted['subtotal']}"
    )
    assert extracted["cgst_amount"] == Decimal("3087.00"), (
        f"Expected CGST 3087.00, got {extracted['cgst_amount']}"
    )
    assert extracted["sgst_amount"] == Decimal("3087.00"), (
        f"Expected SGST 3087.00, got {extracted['sgst_amount']}"
    )
    assert extracted["tax_amount"] == Decimal("6174.00"), (
        f"Expected total tax 6174.00, got {extracted['tax_amount']}"
    )
    assert extracted["total_amount"] == Decimal("40474.00"), (
        f"Expected grand total 40474.00, got {extracted['total_amount']}"
    )

    # 6. Mathematical Reconciliation
    assert extracted["reconciliation_status"] == "RECONCILED"
    calc_sum = extracted["subtotal"] + extracted["cgst_amount"] + extracted["sgst_amount"]
    assert calc_sum == extracted["total_amount"], f"{calc_sum} != {extracted['total_amount']}"

    # 7. Confidence Score & Review flags
    assert extracted["confidence_score"] >= Decimal("85.00"), (
        f"Confidence score {extracted['confidence_score']}% is below expected threshold"
    )
    assert len(extracted["missing_fields"]) == 0


def test_igst_interstate_invoice_extraction():
    """Tests extraction of an Inter-state GST invoice with IGST."""
    text = (
        "TAX INVOICE\n"
        "Skyline Technologies Private Limited\n"
        "GSTIN: 27AABCS1429B1Z1\n"
        "Plot 44, Electronic City, Bengaluru - 560100\n"
        "Billed to: Central University Research Lab\n"
        "Invoice No: SKY-2026-8812\n"
        "Dated: 05/10/2026\n"
        "Place of Supply: Rajasthan (08)\n"
        "Description: Server Rack Mount Chassis and Power Units\n"
        "Taxable Value: ₹50,000.00\n"
        "IGST: ₹9,000.00\n"
        "Grand Total: ₹59,000.00\n"
        "For Skyline Technologies Private Limited\n"
        "Authorised Signatory\n"
    )

    with SessionLocal() as db:
        res = extract_fields_from_text(text, db)

    assert "Skyline Technologies" in res["vendor_name"]
    assert res["tax_identifier"] == "27AABCS1429B1Z1"
    assert res["invoice_number"] == "SKY-2026-8812"
    assert res["invoice_date"] == date(2026, 10, 5)
    assert res["subtotal"] == Decimal("50000.00")
    assert res["igst_amount"] == Decimal("9000.00")
    assert res["tax_amount"] == Decimal("9000.00")
    assert res["total_amount"] == Decimal("59000.00")
    assert res["reconciliation_status"] == "RECONCILED"
    assert res["confidence_score"] >= Decimal("85.00")


def test_discount_and_rounding_adjustments():
    """Tests invoice with trade discount and round-off adjustments:
    Taxable subtotal (10,000.00) - Discount (1,000.00) + CGST (810.00) + SGST (810.00) = 10,620.00.
    """
    text = (
        "TAX INVOICE\n"
        "Premier Lab Equipment Supplies\n"
        "GSTIN: 07AABCP9921D1Z4\n"
        "Invoice Number: PREM-4412\n"
        "Invoice Date: 2026-09-15\n"
        "Taxable Amount: ₹10,000.00\n"
        "Trade Discount: ₹1,000.00\n"
        "CGST: ₹810.00\n"
        "SGST: ₹810.00\n"
        "Rounded Off: ₹0.00\n"
        "Grand Total: ₹10,620.00\n"
        "For Premier Lab Equipment Supplies\n"
    )

    with SessionLocal() as db:
        res = extract_fields_from_text(text, db)

    assert "Premier Lab Equipment" in res["vendor_name"]
    assert res["invoice_number"] == "PREM-4412"
    assert res["subtotal"] == Decimal("10000.00")
    assert res["discount_amount"] == Decimal("1000.00")
    assert res["cgst_amount"] == Decimal("810.00")
    assert res["sgst_amount"] == Decimal("810.00")
    assert res["tax_amount"] == Decimal("1620.00")
    assert res["total_amount"] == Decimal("10620.00")
    assert res["reconciliation_status"] == "RECONCILED"


def test_missing_optional_fields_behavior():
    """Tests that missing optional fields (PO number, due date) remain null
    and do not get marked in missing_fields or penalize valid mandatory data.
    """
    text = (
        "TAX INVOICE\n"
        "Omega Campus Furnishings\n"
        "GSTIN: 08AAECO3391K1Z2\n"
        "Invoice No: OMG-1029\n"
        "Dated: 12-10-2026\n"
        "Taxable Amount: ₹15,000.00\n"
        "Tax Amount: ₹2,700.00\n"
        "Total Amount: ₹17,700.00\n"
        "For Omega Campus Furnishings\n"
    )

    with SessionLocal() as db:
        res = extract_fields_from_text(text, db)

    assert res["purchase_order_number"] is None
    assert res["due_date"] is None
    assert "purchase_order" not in res["missing_fields"]
    assert "due_date" not in res["missing_fields"]
    assert len(res["missing_fields"]) == 0


def test_financial_discrepancy_and_low_confidence_flagging():
    """Tests that an invoice with contradictory financial math is flagged
    with DISCREPANCY, receives a reduced confidence score, and requires review.
    """
    text = (
        "TAX INVOICE\n"
        "Discrepant Vendor Supplies\n"
        "GSTIN: 08AABCV1111A1Z1\n"
        "Invoice No: DISC-999\n"
        "Dated: 2026-11-01\n"
        "Subtotal: ₹10,000.00\n"
        "Tax Amount: ₹1,800.00\n"
        "Total Amount: ₹25,000.00\n"  # Math mismatch: 10000 + 1800 != 25000
        "For Discrepant Vendor Supplies\n"
    )

    with SessionLocal() as db:
        res = extract_fields_from_text(text, db)

    assert res["reconciliation_status"] == "DISCREPANCY"
    assert "Discrepancy" in res["reconciliation_message"]
    # Score should be reduced due to penalty
    assert res["confidence_score"] <= Decimal("70.00")


def test_upload_api_with_sample_invoice_fixture():
    """Tests end-to-end invoice upload API with the sample invoice content,
    verifying GST breakdown and metadata response.
    """
    unique_num = f"9766-{uuid.uuid4().hex[:6].upper()}"
    doc = fitz.open(SAMPLE_PDF_PATH)
    page = doc[0]
    page.insert_text((50, 750), f"Test UID: {unique_num}")
    pdf_bytes = doc.tobytes()
    doc.close()

    res = client.post(
        "/api/v1/invoices/upload",
        files={"file": (f"sample_gst_{unique_num}.pdf", pdf_bytes, "application/pdf")},
        data={"department_id": "1"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["is_duplicate"] is False
    assert float(data["confidence_score"]) >= 85.0

    ext = data["extracted_data"]
    assert ext["vendor_name"] == "Gupta Office Supplies"
    assert ext["tax_identifier"] == "08HWZOU5586H5Z7"
    assert float(ext["subtotal"]) == 34300.00
    assert float(ext["cgst_amount"]) == 3087.00
    assert float(ext["sgst_amount"]) == 3087.00
    assert float(ext["total_amount"]) == 40474.00
    assert ext["reconciliation_status"] == "RECONCILED"


def test_human_review_and_gst_reconciliation_sync():
    """Tests that correcting GST values through the review endpoint updates
    both metadata and tax totals, maintaining reconciliation integrity.
    """
    unique_id = uuid.uuid4().hex[:8].upper()
    pdf_bytes = create_sample_pdf(f"Vendor Testing Draft #{unique_id}")
    upload_res = client.post(
        "/api/v1/invoices/upload",
        files={"file": (f"draft_{unique_id}.pdf", pdf_bytes, "application/pdf")},
    )
    inv_id = upload_res.json()["invoice_id"]

    # Review corrections supplying CGST, SGST, Subtotal, Total
    review_data = {
        "vendor_id": 1,
        "department_id": 1,
        "invoice_number": f"INV-GST-{unique_id}",
        "invoice_date": "2026-11-10",
        "due_date": "2026-12-10",
        "subtotal": "34300.00",
        "cgst_amount": "3087.00",
        "sgst_amount": "3087.00",
        "total_amount": "40474.00",
        "currency": "INR",
        "tax_identifier": "08HWZOU5586H5Z7",
        "customer_name": "Central University Accounts",
    }
    rev_res = client.post(f"/api/v1/invoices/{inv_id}/review", json=review_data)
    assert rev_res.status_code == 200
    updated = rev_res.json()
    assert float(updated["tax_amount"]) == 6174.00
    assert float(updated["total_amount"]) == 40474.00

    # Validate invoice
    val_res = client.post(f"/api/v1/invoices/{inv_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["success"] is True
    assert val_data["processing_status"] == "VALIDATED"
