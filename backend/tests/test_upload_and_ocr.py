import io
import uuid
from decimal import Decimal
import fitz
from PIL import Image, ImageDraw
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def create_sample_pdf(text: str) -> bytes:
    """Helper to generate a valid digital PDF in-memory using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_sample_png(text: str) -> bytes:
    """Helper to generate a valid PNG image in-memory."""
    img = Image.new("RGB", (500, 150), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((20, 50), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_sample_jpeg(text: str) -> bytes:
    """Helper to generate a valid JPEG image in-memory."""
    img = Image.new("RGB", (500, 150), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((20, 50), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_successful_pdf_upload_and_extraction():
    """Tests uploading a realistic university invoice PDF and verifies OCR extraction."""
    unique_id = uuid.uuid4().hex[:8].upper()
    inv_num = f"INV-2025-{unique_id}"
    pdf_content = (
        "Apex Computing Solutions Inc.\n"
        "Vendor Code: VND-TECH-01\n"
        "Tax ID: US-EIN-74-3928172\n"
        f"Invoice Number: {inv_num}\n"
        "PO Number: PO-2024-001\n"
        "Date of Issue: 2025-01-15\n"
        "Payment Due: 2025-02-15\n\n"
        "Description: Cloud Server Node Maintenance and Support\n"
        "Subtotal: $4,000.00\n"
        "Tax Amount: $720.00\n"
        "Total Amount Due: $4,720.00\n"
    )
    pdf_bytes = create_sample_pdf(pdf_content)

    response = client.post(
        "/api/v1/invoices/upload",
        files={"file": (f"invoice_{unique_id}.pdf", pdf_bytes, "application/pdf")},
        data={"department_id": "1"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["invoice_number"] == inv_num
    assert data["is_duplicate"] is False
    assert data["mime_type"] == "application/pdf"
    assert data["ocr_method"] == "PYMUPDF_DIGITAL"
    assert data["confidence_score"] is not None
    assert float(data["confidence_score"]) >= 70.0
    assert data["processing_status"] in ["EXTRACTED", "NEEDS_REVIEW"]

    # Verify extracted data payload
    ext = data["extracted_data"]
    assert ext["vendor_code"] == "VND-TECH-01"
    assert ext["purchase_order_number"] == "PO-2024-001"
    assert float(ext["total_amount"]) == 4720.00
    assert float(ext["subtotal"]) == 4000.00
    assert float(ext["tax_amount"]) == 720.00


def test_successful_image_upload():
    """Tests uploading PNG and JPEG images with file signature verification."""
    unique_id = uuid.uuid4().hex[:8].upper()
    png_bytes = create_sample_png(f"INVOICE #INV-PNG-{unique_id} Total: $1,250.00")
    res_png = client.post(
        "/api/v1/invoices/upload",
        files={"file": (f"receipt_{unique_id}.png", png_bytes, "image/png")},
    )
    assert res_png.status_code == 201
    data_png = res_png.json()
    assert data_png["mime_type"] == "image/png"
    assert data_png["ocr_method"] == "TESSERACT_OCR"

    unique_jpg_id = uuid.uuid4().hex[:8].upper()
    jpeg_bytes = create_sample_jpeg(f"INVOICE #INV-JPG-{unique_jpg_id} Total: $850.00")
    res_jpg = client.post(
        "/api/v1/invoices/upload",
        files={"file": (f"receipt_{unique_jpg_id}.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert res_jpg.status_code == 201
    data_jpg = res_jpg.json()
    assert data_jpg["mime_type"] == "image/jpeg"
    assert data_jpg["ocr_method"] == "TESSERACT_OCR"


def test_reject_unsupported_file_types():
    """Tests rejection of unsupported extensions and malicious extensions."""
    exe_content = b"MZ\x90\x00\x03\x00\x00\x00"
    res = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("virus.exe", exe_content, "application/octet-stream")},
    )
    assert res.status_code == 400
    assert "unsupported" in res.json()["detail"].lower()

    txt_content = b"Simple invoice text without pdf header"
    res_txt = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("invoice.txt", txt_content, "text/plain")},
    )
    assert res_txt.status_code == 400


def test_reject_empty_and_malformed_files():
    """Tests rejection of 0-byte files and fake signature files."""
    # Empty file
    res_empty = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert res_empty.status_code == 400
    assert "empty" in res_empty.json()["detail"].lower()

    # Fake PDF (has .pdf extension but content is random garbage)
    res_fake = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("corrupt.pdf", b"This is not a real PDF document", "application/pdf")},
    )
    assert res_fake.status_code == 400
    assert "signature" in res_fake.json()["detail"].lower()


def test_reject_oversized_files():
    """Tests rejection of files exceeding 10 MB limit."""
    oversized = b"%PDF-1.4 " + (b"0" * (10 * 1024 * 1024 + 1024))
    res = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("huge_invoice.pdf", oversized, "application/pdf")},
    )
    assert res.status_code == 400
    assert "exceeds maximum limit" in res.json()["detail"].lower()


def test_sha256_duplicate_detection():
    """Tests that uploading an identical file twice triggers SHA-256 duplicate warning."""
    unique_dup_id = uuid.uuid4().hex[:8].upper()
    pdf_bytes = create_sample_pdf(f"Apex Computing Solutions Inc. INVOICE INV-DUP-{unique_dup_id} Total $500.00")

    # First upload
    res1 = client.post(
        "/api/v1/invoices/upload",
        files={"file": (f"first_{unique_dup_id}.pdf", pdf_bytes, "application/pdf")},
    )
    assert res1.status_code == 201
    assert res1.json()["is_duplicate"] is False

    # Second upload of exact same bytes
    res2 = client.post(
        "/api/v1/invoices/upload",
        files={"file": (f"second_{unique_dup_id}.pdf", pdf_bytes, "application/pdf")},
    )
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["is_duplicate"] is True
    assert "identical document" in data2["duplicate_warning"].lower()
    assert data2["processing_status"] == "DUPLICATE"


def test_secure_document_download_and_extraction_endpoint():
    """Tests secure streaming download of uploaded document and extraction telemetry."""
    unique_id = uuid.uuid4().hex[:8].upper()
    pdf_bytes = create_sample_pdf(f"University AP Test Doc - Invoice INV-STREAM-{unique_id}")
    upload_res = client.post(
        "/api/v1/invoices/upload",
        files={"file": (f"stream_{unique_id}.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_res.status_code == 201
    inv_id = upload_res.json()["invoice_id"]

    # 1. Test secure document download
    doc_res = client.get(f"/api/v1/invoices/{inv_id}/document")
    assert doc_res.status_code == 200
    assert doc_res.content.startswith(b"%PDF")

    # 2. Test extraction telemetry endpoint
    ext_res = client.get(f"/api/v1/invoices/{inv_id}/extraction")
    assert ext_res.status_code == 200
    ext_data = ext_res.json()
    assert ext_data["invoice_id"] == inv_id
    assert "raw_text" in ext_data
    assert "confidence_score" in ext_data


def test_human_review_and_invoice_validation():
    """Tests human review correction and strict validation workflow."""
    unique_id = uuid.uuid4().hex[:8].upper()
    pdf_bytes = create_sample_pdf(f"Rough receipt {unique_id} without dates or vendor. Amount $1,500.00")
    res = client.post(
        "/api/v1/invoices/upload",
        files={"file": (f"incomplete_{unique_id}.pdf", pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 201
    inv_id = res.json()["invoice_id"]

    # Attempt to validate prematurely (should fail 422 with clear errors)
    val_fail = client.post(f"/api/v1/invoices/{inv_id}/validate")
    assert val_fail.status_code == 422
    assert "validation failed" in val_fail.json()["detail"]["message"].lower()

    # Staff performs review corrections
    review_payload = {
        "vendor_id": 1,
        "department_id": 1,
        "invoice_number": f"INV-VALID-{unique_id}",
        "invoice_date": "2025-01-10",
        "due_date": "2025-02-10",
        "subtotal": "1271.19",
        "tax_amount": "228.81",
        "total_amount": "1500.00",
        "currency": "USD",
        "description": "Validated Lab Equipment Supplies",
    }
    review_res = client.post(f"/api/v1/invoices/{inv_id}/review", json=review_payload)
    assert review_res.status_code == 200
    updated = review_res.json()
    assert updated["vendor_id"] == 1
    assert updated["invoice_number"] == f"INV-VALID-{unique_id}"

    # Now validate after corrections (should succeed)
    val_success = client.post(f"/api/v1/invoices/{inv_id}/validate")
    assert val_success.status_code == 200
    val_data = val_success.json()
    assert val_data["success"] is True
    assert val_data["processing_status"] == "VALIDATED"


def test_validation_rejects_financial_inconsistency():
    """Tests that validation rejects math mismatches between subtotal + tax and total."""
    unique_id = uuid.uuid4().hex[:8].upper()
    pdf_bytes = create_sample_pdf(f"Invoice for math validation test {unique_id}")
    res = client.post(
        "/api/v1/invoices/upload",
        files={"file": (f"math_{unique_id}.pdf", pdf_bytes, "application/pdf")},
    )
    inv_id = res.json()["invoice_id"]

    corrections = {
        "vendor_id": 1,
        "department_id": 1,
        "invoice_number": f"INV-MATH-{unique_id}",
        "invoice_date": "2025-01-10",
        "due_date": "2025-02-10",
        "subtotal": "1000.00",
        "tax_amount": "100.00",
        "total_amount": "2000.00",  # Math inconsistency!
    }
    client.post(f"/api/v1/invoices/{inv_id}/review", json=corrections)

    val_res = client.post(f"/api/v1/invoices/{inv_id}/validate")
    assert val_res.status_code == 422
    errors = val_res.json()["detail"]["errors"]
    assert any("financial inconsistency" in err.lower() for err in errors)
