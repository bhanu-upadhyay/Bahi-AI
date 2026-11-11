from datetime import date, datetime, timezone
from decimal import Decimal
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import (
    Invoice,
    InvoiceLine,
    normalize_invoice_number,
    AuditLog,
    AgentExecutionLog,
    FraudAlert,
    Vendor,
    Department,
    PurchaseOrder,
)
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceDetailResponse,
    InvoiceResponse,
    InvoiceReviewUpdate,
    InvoiceUpdate,
    InvoiceUploadResponse,
    InvoiceValidationResponse,
)
from app.utils.file_handler import (
    FileValidationError,
    get_absolute_file_path,
    save_uploaded_file,
    sanitize_filename,
)
from app.services.ocr_service import (
    OCRExtractionError,
    extract_document_text,
)
from app.services.extraction_service import (
    detect_duplicates,
    extract_fields_from_text,
)

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("", response_model=List[InvoiceResponse])
def list_invoices(
    status: Optional[str] = Query(None, description="Filter by processing status"),
    approval_status: Optional[str] = Query(None, description="Filter by approval status"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    vendor_id: Optional[int] = Query(None, description="Filter by vendor"),
    search: Optional[str] = Query(None, description="Search by invoice number or vendor"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List invoices with optional filters and pagination."""
    query = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.vendor),
            joinedload(Invoice.department),
            joinedload(Invoice.lines),
        )
    )

    if status:
        query = query.filter(Invoice.processing_status == status.upper())
    if approval_status:
        query = query.filter(Invoice.approval_status == approval_status.upper())
    if payment_status:
        query = query.filter(Invoice.payment_status == payment_status.upper())
    if department_id:
        query = query.filter(Invoice.department_id == department_id)
    if vendor_id:
        query = query.filter(Invoice.vendor_id == vendor_id)
    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.join(Invoice.vendor, isouter=True).filter(
            or_(
                Invoice.invoice_number.ilike(search_fmt),
                Invoice.normalized_invoice_number.ilike(search_fmt),
                Vendor.legal_name.ilike(search_fmt),
            )
        )

    invoices = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    return invoices


@router.post("/upload", response_model=InvoiceUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    file: UploadFile = File(..., description="Invoice document (PDF, PNG, JPG/JPEG up to 10MB)"),
    department_id: Optional[int] = Form(None, description="Optional target department ID"),
    db: Session = Depends(get_db),
):
    """Uploads an invoice document, performs OCR extraction, checks duplicates,
    and saves an initial invoice record for human review and validation.
    """
    start_time = time.time()
    raw_content = await file.read()
    orig_filename = sanitize_filename(file.filename or "uploaded_invoice.pdf")

    # 1. Validate file content and signature
    try:
        rel_path, server_filename, file_size, sha256_hash = save_uploaded_file(raw_content, orig_filename)
    except FileValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Detect mime type for OCR
    mime_type = "application/pdf" if orig_filename.lower().endswith(".pdf") else "image/png"
    if orig_filename.lower().endswith((".jpg", ".jpeg")):
        mime_type = "image/jpeg"

    # 2. Check for exact document duplicate (SHA-256)
    is_file_dup, file_dup_reason, existing_dup_id = detect_duplicates(
        db=db,
        file_hash=sha256_hash,
        vendor_id=None,
        invoice_number=None,
    )

    # 3. Perform OCR / text extraction
    raw_text = ""
    ocr_method = "UNKNOWN"
    ocr_error_msg = None
    try:
        abs_file_path = get_absolute_file_path(rel_path)
        raw_text, ocr_method, ocr_meta = extract_document_text(abs_file_path, mime_type)
    except OCRExtractionError as e:
        ocr_error_msg = str(e)
        ocr_meta = {"error": ocr_error_msg}

    # 4. Extract structured fields from text
    extracted = extract_fields_from_text(raw_text, db)
    assigned_dept_id = department_id or None

    # Determine invoice number (fallback to generated placeholder if OCR didn't find one)
    extracted_inv_num = extracted.get("invoice_number")
    if not extracted_inv_num:
        extracted_inv_num = f"PENDING-{server_filename[:8].upper()}"

    normalized_inv_num = normalize_invoice_number(extracted_inv_num)

    # 5. Check for vendor + invoice number duplicate
    is_logical_dup = False
    logical_dup_reason = None
    if extracted.get("vendor_id") and extracted.get("invoice_number"):
        is_logical_dup, logical_dup_reason, existing_dup_id = detect_duplicates(
            db=db,
            file_hash=None,
            vendor_id=extracted["vendor_id"],
            invoice_number=extracted["invoice_number"],
        )

    is_duplicate = is_file_dup or is_logical_dup
    duplicate_warning = file_dup_reason or logical_dup_reason

    # 6. Determine processing status
    if is_duplicate:
        proc_status = "DUPLICATE"
        extract_status = "EXTRACTED" if raw_text else "FAILED"
        # Ensure duplicate invoice does not collide with existing unique constraint
        normalized_inv_num = f"{normalized_inv_num}-DUP-{server_filename[:6].upper()}"
    elif ocr_error_msg or len(raw_text.strip()) == 0:
        proc_status = "FAILED"
        extract_status = "FAILED"
    elif len(extracted["missing_fields"]) > 0 or extracted["confidence_score"] < Decimal("70.00"):
        proc_status = "NEEDS_REVIEW"
        extract_status = "NEEDS_REVIEW"
    else:
        proc_status = "EXTRACTED"
        extract_status = "EXTRACTED"

    # Merge extraction metadata
    meta = {
        "ocr_meta": ocr_meta,
        "missing_fields": extracted["missing_fields"],
        "field_confidences": extracted["field_confidences"],
        "duplicate_warning": duplicate_warning,
    }

    # 7. Create Invoice database record
    new_invoice = Invoice(
        invoice_number=extracted_inv_num,
        normalized_invoice_number=normalized_inv_num,
        vendor_id=extracted.get("vendor_id"),
        purchase_order_id=extracted.get("purchase_order_id"),
        department_id=assigned_dept_id,
        invoice_date=extracted.get("invoice_date"),
        due_date=extracted.get("due_date"),
        subtotal=extracted.get("subtotal") or Decimal("0.00"),
        tax_amount=extracted.get("tax_amount") or Decimal("0.00"),
        total_amount=extracted.get("total_amount") or Decimal("0.00"),
        currency=extracted.get("currency") or "USD",
        description=extracted.get("description"),
        tax_identifier=extracted.get("tax_identifier"),
        document_path=rel_path,
        original_filename=orig_filename,
        file_hash=sha256_hash,
        file_size=file_size,
        mime_type=mime_type,
        raw_text=raw_text,
        ocr_method=ocr_method,
        confidence_score=extracted.get("confidence_score"),
        extraction_metadata=meta,
        extraction_status=extract_status,
        processing_status=proc_status,
        approval_status="PENDING",
        payment_status="UNPAID",
    )
    db.add(new_invoice)
    db.flush()

    duration = Decimal(str(round(time.time() - start_time, 4)))

    # If duplicate, create fraud alert
    if is_duplicate:
        alert = FraudAlert(
            invoice_id=new_invoice.id,
            alert_type="DUPLICATE_INVOICE",
            severity="CRITICAL" if is_file_dup else "HIGH",
            description=f"Duplicate detected during intake: {duplicate_warning}",
            risk_score=Decimal("95.00"),
            status="OPEN",
        )
        db.add(alert)

    # 8. Append Audit Logs
    audit_upload = AuditLog(
        action="DOCUMENT_UPLOADED",
        entity_type="INVOICE",
        entity_id=str(new_invoice.id),
        new_values={
            "original_filename": orig_filename,
            "file_size": file_size,
            "file_hash": sha256_hash,
            "ocr_method": ocr_method,
        },
    )
    db.add(audit_upload)

    audit_ocr = AuditLog(
        action="OCR_EXTRACTION_COMPLETED" if raw_text else "OCR_EXTRACTION_FAILED",
        entity_type="INVOICE",
        entity_id=str(new_invoice.id),
        new_values={
            "ocr_method": ocr_method,
            "confidence_score": float(extracted.get("confidence_score") or 0),
            "missing_fields": extracted["missing_fields"],
            "processing_status": proc_status,
        },
    )
    db.add(audit_ocr)

    if is_duplicate:
        audit_dup = AuditLog(
            action="DUPLICATE_DOCUMENT_DETECTED",
            entity_type="INVOICE",
            entity_id=str(new_invoice.id),
            new_values={"reason": duplicate_warning, "existing_invoice_id": existing_dup_id},
        )
        db.add(audit_dup)

    # Agent Execution Log for IntakeAgent
    agent_log = AgentExecutionLog(
        invoice_id=new_invoice.id,
        agent_name="IntakeAgent",
        execution_status="COMPLETED" if raw_text else "FAILED",
        input_summary=f"Processed document {orig_filename} ({file_size} bytes, {mime_type})",
        output_summary=f"Method: {ocr_method}, Conf: {extracted.get('confidence_score')}%, Status: {proc_status}",
        error_message=ocr_error_msg,
        execution_duration=duration,
    )
    db.add(agent_log)

    db.commit()
    db.refresh(new_invoice)

    return InvoiceUploadResponse(
        invoice_id=new_invoice.id,
        invoice_number=new_invoice.invoice_number,
        original_filename=orig_filename,
        file_hash=sha256_hash,
        file_size=file_size,
        mime_type=mime_type,
        ocr_method=ocr_method,
        confidence_score=new_invoice.confidence_score,
        processing_status=new_invoice.processing_status,
        extraction_status=new_invoice.extraction_status,
        is_duplicate=is_duplicate,
        duplicate_warning=duplicate_warning,
        duplicate_invoice_id=existing_dup_id,
        extracted_data=extracted,
    )


@router.get("/{invoice_id}/document")
def get_invoice_document(invoice_id: int, db: Session = Depends(get_db)):
    """Securely streams the uploaded invoice document to authorized users.
    Never exposes files through unrestricted static file serving.
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice or not invoice.document_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice document not found in records",
        )

    try:
        abs_path = get_absolute_file_path(invoice.document_path)
    except (FileNotFoundError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    filename = invoice.original_filename or f"invoice_{invoice_id}.pdf"
    media_type = invoice.mime_type or "application/pdf"
    return FileResponse(path=str(abs_path), media_type=media_type, filename=filename)


@router.get("/{invoice_id}/extraction")
def get_invoice_extraction(invoice_id: int, db: Session = Depends(get_db)):
    """Retrieves detailed OCR raw text, extraction confidence, and duplicate indicators."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "original_filename": invoice.original_filename,
        "file_hash": invoice.file_hash,
        "ocr_method": invoice.ocr_method,
        "raw_text": invoice.raw_text,
        "confidence_score": invoice.confidence_score,
        "extraction_metadata": invoice.extraction_metadata,
        "processing_status": invoice.processing_status,
        "extraction_status": invoice.extraction_status,
        "created_at": invoice.created_at,
    }


@router.post("/{invoice_id}/review", response_model=InvoiceDetailResponse)
def review_and_correct_invoice(
    invoice_id: int,
    corrections: InvoiceReviewUpdate,
    db: Session = Depends(get_db),
):
    """Allows staff to correct extracted invoice fields during human review."""
    invoice = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.vendor),
            joinedload(Invoice.department),
            joinedload(Invoice.purchase_order),
            joinedload(Invoice.lines),
            joinedload(Invoice.approvals),
            joinedload(Invoice.payments),
            joinedload(Invoice.fraud_alerts),
        )
        .filter(Invoice.id == invoice_id)
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    old_values = {
        "vendor_id": invoice.vendor_id,
        "department_id": invoice.department_id,
        "invoice_number": invoice.invoice_number,
        "total_amount": float(invoice.total_amount) if invoice.total_amount else None,
        "invoice_date": str(invoice.invoice_date) if invoice.invoice_date else None,
        "due_date": str(invoice.due_date) if invoice.due_date else None,
    }

    if corrections.vendor_id is not None:
        invoice.vendor_id = corrections.vendor_id
    if corrections.department_id is not None:
        invoice.department_id = corrections.department_id
    if corrections.invoice_number is not None:
        invoice.invoice_number = corrections.invoice_number
        invoice.normalized_invoice_number = normalize_invoice_number(corrections.invoice_number)
    if corrections.invoice_date is not None:
        invoice.invoice_date = corrections.invoice_date
    if corrections.due_date is not None:
        invoice.due_date = corrections.due_date
    if corrections.purchase_order_id is not None:
        invoice.purchase_order_id = corrections.purchase_order_id
    if corrections.subtotal is not None:
        invoice.subtotal = corrections.subtotal
    if corrections.tax_amount is not None:
        invoice.tax_amount = corrections.tax_amount
    if corrections.total_amount is not None:
        invoice.total_amount = corrections.total_amount
    if corrections.currency is not None:
        invoice.currency = corrections.currency
    if corrections.description is not None:
        invoice.description = corrections.description
    if corrections.tax_identifier is not None:
        invoice.tax_identifier = corrections.tax_identifier

    # Audit logging for correction
    audit = AuditLog(
        action="INVOICE_FIELDS_CORRECTED",
        entity_type="INVOICE",
        entity_id=str(invoice.id),
        old_values=old_values,
        new_values={
            "vendor_id": invoice.vendor_id,
            "department_id": invoice.department_id,
            "invoice_number": invoice.invoice_number,
            "total_amount": float(invoice.total_amount) if invoice.total_amount else None,
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/validate", response_model=InvoiceValidationResponse)
def validate_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Validates that extracted invoice contains all required fields, valid dates,
    positive amounts, and internal consistency. Transitions status to VALIDATED.
    """
    invoice = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.vendor),
            joinedload(Invoice.department),
            joinedload(Invoice.purchase_order),
            joinedload(Invoice.lines),
            joinedload(Invoice.approvals),
            joinedload(Invoice.payments),
            joinedload(Invoice.fraud_alerts),
        )
        .filter(Invoice.id == invoice_id)
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    errors = []

    # Required field validation
    if not invoice.invoice_number or invoice.invoice_number.startswith("PENDING-"):
        errors.append("Valid invoice number is required.")
    if not invoice.vendor_id:
        errors.append("Vendor must be selected and linked.")
    if not invoice.department_id:
        errors.append("Department must be selected.")
    if not invoice.invoice_date:
        errors.append("Invoice date is required.")
    if not invoice.due_date:
        errors.append("Due date is required.")
    if not invoice.total_amount or invoice.total_amount <= Decimal("0.00"):
        errors.append("Total amount must be greater than 0.00.")

    # Date ordering validation
    if invoice.invoice_date and invoice.due_date and invoice.due_date < invoice.invoice_date:
        errors.append("Due date cannot be earlier than invoice date.")

    # Monetary consistency validation (subtotal + tax ~= total within 0.05 tolerance)
    if invoice.total_amount and invoice.subtotal is not None and invoice.tax_amount is not None:
        calc_total = invoice.subtotal + invoice.tax_amount
        if abs(calc_total - invoice.total_amount) > Decimal("0.05"):
            errors.append(
                f"Financial inconsistency: Subtotal ({invoice.subtotal}) + Tax ({invoice.tax_amount}) = {calc_total}, which does not match Total Amount ({invoice.total_amount})."
            )

    # Check for duplicate against other invoices
    if invoice.vendor_id and invoice.invoice_number:
        norm = normalize_invoice_number(invoice.invoice_number)
        dup = (
            db.query(Invoice)
            .filter(
                Invoice.id != invoice.id,
                Invoice.vendor_id == invoice.vendor_id,
                Invoice.normalized_invoice_number == norm,
            )
            .first()
        )
        if dup:
            errors.append(f"Duplicate invoice: Invoice '{invoice.invoice_number}' already exists for this vendor (ID: {dup.id}).")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": errors, "message": "Invoice validation failed."},
        )

    # Transition status
    invoice.processing_status = "VALIDATED"
    invoice.extraction_status = "EXTRACTED"

    # Append audit log
    audit = AuditLog(
        action="INVOICE_VALIDATED",
        entity_type="INVOICE",
        entity_id=str(invoice.id),
        new_values={
            "invoice_number": invoice.invoice_number,
            "vendor_id": invoice.vendor_id,
            "total_amount": float(invoice.total_amount),
            "status": "VALIDATED",
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(invoice)

    return InvoiceValidationResponse(
        success=True,
        invoice_id=invoice.id,
        processing_status=invoice.processing_status,
        message="Invoice validated successfully and registered for approval and matching.",
        invoice=invoice,
    )


@router.get("/{invoice_id}", response_model=InvoiceDetailResponse)
def get_invoice_detail(invoice_id: int, db: Session = Depends(get_db)):
    """Fetch complete invoice details with lines, PO, approvals, payments, and alerts."""
    invoice = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.vendor),
            joinedload(Invoice.department),
            joinedload(Invoice.purchase_order),
            joinedload(Invoice.lines),
            joinedload(Invoice.approvals),
            joinedload(Invoice.payments),
            joinedload(Invoice.fraud_alerts),
        )
        .filter(Invoice.id == invoice_id)
        .first()
    )

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID {invoice_id} not found",
        )

    return invoice


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(invoice_in: InvoiceCreate, db: Session = Depends(get_db)):
    """Create a new invoice with duplicate protection via normalized invoice number."""
    normalized = normalize_invoice_number(invoice_in.invoice_number)

    if invoice_in.vendor_id:
        existing = (
            db.query(Invoice)
            .filter(
                Invoice.vendor_id == invoice_in.vendor_id,
                Invoice.normalized_invoice_number == normalized,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate invoice detected: Invoice '{invoice_in.invoice_number}' already exists for this vendor.",
            )

    new_invoice = Invoice(
        invoice_number=invoice_in.invoice_number,
        normalized_invoice_number=normalized,
        vendor_id=invoice_in.vendor_id,
        purchase_order_id=invoice_in.purchase_order_id,
        department_id=invoice_in.department_id,
        invoice_date=invoice_in.invoice_date,
        due_date=invoice_in.due_date,
        subtotal=invoice_in.subtotal,
        tax_amount=invoice_in.tax_amount,
        total_amount=invoice_in.total_amount,
        currency=invoice_in.currency,
        description=invoice_in.description,
        tax_identifier=invoice_in.tax_identifier,
        document_path=invoice_in.document_path,
        original_filename=invoice_in.original_filename,
        extraction_status=invoice_in.extraction_status,
        processing_status=invoice_in.processing_status,
        approval_status=invoice_in.approval_status,
        payment_status=invoice_in.payment_status,
    )
    db.add(new_invoice)
    db.flush()

    for line_in in invoice_in.lines:
        new_line = InvoiceLine(
            invoice_id=new_invoice.id,
            line_number=line_in.line_number,
            description=line_in.description,
            quantity=line_in.quantity,
            unit_price=line_in.unit_price,
            tax_rate=line_in.tax_rate,
            line_total=line_in.line_total,
        )
        db.add(new_line)

    audit_entry = AuditLog(
        action="INVOICE_CREATED",
        entity_type="INVOICE",
        entity_id=str(new_invoice.id),
        new_values={
            "invoice_number": new_invoice.invoice_number,
            "vendor_id": new_invoice.vendor_id,
            "total_amount": float(new_invoice.total_amount) if new_invoice.total_amount else 0.0,
        },
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(new_invoice)
    return new_invoice


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(invoice_id: int, invoice_update: InvoiceUpdate, db: Session = Depends(get_db)):
    """Update invoice status or metadata."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    old_values = {
        "processing_status": invoice.processing_status,
        "approval_status": invoice.approval_status,
        "payment_status": invoice.payment_status,
    }

    if invoice_update.processing_status is not None:
        invoice.processing_status = invoice_update.processing_status
    if invoice_update.approval_status is not None:
        invoice.approval_status = invoice_update.approval_status
    if invoice_update.payment_status is not None:
        invoice.payment_status = invoice_update.payment_status
    if invoice_update.due_date is not None:
        invoice.due_date = invoice_update.due_date

    audit = AuditLog(
        action="INVOICE_UPDATED",
        entity_type="INVOICE",
        entity_id=str(invoice.id),
        old_values=old_values,
        new_values={
            "processing_status": invoice.processing_status,
            "approval_status": invoice.approval_status,
            "payment_status": invoice.payment_status,
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(invoice)
    return invoice
