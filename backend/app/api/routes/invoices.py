from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import (
    Invoice,
    InvoiceLine,
    normalize_invoice_number,
    AuditLog,
)
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceDetailResponse,
    InvoiceResponse,
    InvoiceUpdate,
)

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("", response_model=List[InvoiceResponse])
def list_invoices(
    status: Optional[str] = Query(None, description="Filter by processing status"),
    approval_status: Optional[str] = Query(None, description="Filter by approval status"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    vendor_id: Optional[int] = Query(None, description="Filter by vendor"),
    search: Optional[str] = Query(None, description="Search by invoice number"),
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
        query = query.filter(
            or_(
                Invoice.invoice_number.ilike(search_fmt),
                Invoice.normalized_invoice_number.ilike(search_fmt),
            )
        )

    invoices = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    return invoices


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

    # Check for duplicate
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

    # Append-only audit log
    audit_entry = AuditLog(
        action="INVOICE_CREATED",
        entity_type="INVOICE",
        entity_id=str(new_invoice.id),
        new_values={
            "invoice_number": new_invoice.invoice_number,
            "vendor_id": new_invoice.vendor_id,
            "total_amount": float(new_invoice.total_amount),
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

    # Record in audit log
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

