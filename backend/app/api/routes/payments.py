from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import FINANCE_ROLES, require_roles
from app.models.audit_log import AuditLog
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.user import User
from app.schemas.erp import (
    InvoicePaymentBalanceResponse,
    PaymentPreparationRequest,
    PaymentPreparationResponse,
)
from app.schemas.payment import PaymentCreate, PaymentResponse

router = APIRouter(prefix="/payments", tags=["Payments"])


def _calculate_invoice_balance(invoice: Invoice, db: Session) -> dict:
    """Computes total invoiced, total settled, and outstanding balance."""
    payments = db.query(Payment).filter(Payment.invoice_id == invoice.id).all()
    total_invoiced = Decimal(str(invoice.total_amount or "0.00"))
    settled_amount = sum(
        Decimal(str(p.amount)) for p in payments if p.status in ["COMPLETED", "PAID"]
    )
    scheduled_amount = sum(
        Decimal(str(p.amount)) for p in payments if p.status in ["SCHEDULED", "PROCESSING"]
    )
    outstanding = max(Decimal("0.00"), total_invoiced - settled_amount)
    is_fully_paid = outstanding <= Decimal("0.00") and total_invoiced > Decimal("0.00")

    return {
        "total_invoiced": total_invoiced,
        "settled_amount": settled_amount,
        "scheduled_amount": scheduled_amount,
        "outstanding_balance": outstanding,
        "is_fully_paid": is_fully_paid,
        "payments": payments,
    }


@router.get("", response_model=List[PaymentResponse])
def list_payments(
    status: Optional[str] = Query(None, description="Filter by payment status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List mock payment batches and scheduled transactions."""
    query = db.query(Payment)
    if status:
        query = query.filter(Payment.status == status.upper())
    return query.order_by(Payment.scheduled_date.desc(), Payment.id.desc()).offset(skip).limit(limit).all()


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    """Get single payment record details."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")
    return payment


@router.get("/invoice/{invoice_id}/balance", response_model=InvoicePaymentBalanceResponse)
def get_invoice_payment_balance(invoice_id: int, db: Session = Depends(get_db)):
    """Calculates total invoiced, settled amounts, and outstanding balance for an invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    balance_info = _calculate_invoice_balance(invoice, db)
    payments_data = [
        {
            "id": p.id,
            "reference": p.payment_reference,
            "amount": float(p.amount),
            "status": p.status,
            "method": p.payment_method,
            "scheduled_date": str(p.scheduled_date),
            "payment_date": str(p.payment_date) if p.payment_date else None,
        }
        for p in balance_info["payments"]
    ]

    return InvoicePaymentBalanceResponse(
        invoice_id=invoice.id,
        invoice_number=invoice.invoice_number,
        total_invoiced_amount=balance_info["total_invoiced"],
        total_paid_amount=balance_info["settled_amount"],
        outstanding_balance=balance_info["outstanding_balance"],
        is_fully_paid=balance_info["is_fully_paid"],
        payment_status=invoice.payment_status,
        payments=payments_data,
    )


@router.post("/prepare", response_model=PaymentPreparationResponse)
def prepare_payment(
    req: PaymentPreparationRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(require_roles(*FINANCE_ROLES)),
):
    """Prepares and schedules a partial or full payment with balance verification.
    Protected by RBAC: only authorized finance administrators and officers may schedule disbursements.
    """
    invoice = db.query(Invoice).filter(Invoice.id == req.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Payment must only be initiated for an approved invoice
    if invoice.approval_status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment preparation blocked: Invoice #{invoice.invoice_number} is not approved (Status: {invoice.approval_status}).",
        )

    balance_info = _calculate_invoice_balance(invoice, db)
    req_amt = Decimal(str(req.amount))

    if req_amt > balance_info["outstanding_balance"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Requested payment amount ({invoice.currency} {req_amt}) exceeds "
                f"outstanding invoice balance ({invoice.currency} {balance_info['outstanding_balance']})."
            ),
        )

    # Generate unique payment reference
    hash_suffix = hashlib.sha256(f"{invoice.id}-{req_amt}-{req.scheduled_date}-{datetime.now()}".encode()).hexdigest()[:6].upper()
    payment_ref = f"PAY-{req.scheduled_date.year}-{invoice.id:04d}-{hash_suffix}"

    payment = Payment(
        invoice_id=invoice.id,
        payment_reference=payment_ref,
        scheduled_date=req.scheduled_date,
        amount=req_amt,
        status="SCHEDULED",
        payment_method=req.payment_method.upper(),
        external_reference=req.comments,
    )
    db.add(payment)
    invoice.payment_status = "SCHEDULED"

    remaining = balance_info["outstanding_balance"] - req_amt

    audit = AuditLog(
        action="PAYMENT_PREPARED",
        entity_type="PAYMENT",
        entity_id=payment.payment_reference,
        new_values={
            "invoice_id": invoice.id,
            "amount": float(payment.amount),
            "scheduled_date": str(payment.scheduled_date),
            "remaining_balance": float(remaining),
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(payment)

    return PaymentPreparationResponse(
        payment_id=payment.id,
        invoice_id=invoice.id,
        payment_reference=payment.payment_reference,
        amount=payment.amount,
        scheduled_date=payment.scheduled_date,
        payment_method=payment.payment_method,
        status=payment.status,
        remaining_balance_after=remaining,
        message=f"Disbursement of {invoice.currency} {req_amt} scheduled successfully.",
    )


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def schedule_payment(payment_in: PaymentCreate, db: Session = Depends(get_db)):
    """Schedule a new disbursement for an approved invoice (standard compatibility route)."""
    invoice = db.query(Invoice).filter(Invoice.id == payment_in.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    balance_info = _calculate_invoice_balance(invoice, db)
    req_amt = Decimal(str(payment_in.amount))

    if req_amt > balance_info["outstanding_balance"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount ({req_amt}) exceeds outstanding invoice balance ({balance_info['outstanding_balance']}).",
        )

    payment = Payment(
        invoice_id=payment_in.invoice_id,
        payment_reference=payment_in.payment_reference,
        scheduled_date=payment_in.scheduled_date,
        amount=payment_in.amount,
        status="SCHEDULED",
        payment_method=payment_in.payment_method,
        external_reference=payment_in.external_reference,
    )
    db.add(payment)
    invoice.payment_status = "SCHEDULED"

    audit = AuditLog(
        action="PAYMENT_SCHEDULED",
        entity_type="PAYMENT",
        entity_id=payment.payment_reference,
        new_values={
            "invoice_id": invoice.id,
            "amount": float(payment.amount),
            "scheduled_date": str(payment.scheduled_date),
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/{payment_id}/simulate", response_model=PaymentResponse)
def simulate_payment_settlement(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(require_roles(*FINANCE_ROLES)),
):
    """Simulate mock payment settlement and bank confirmation.
    Protected by RBAC: only authorized finance administrators and officers may simulate settlement.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Prevent duplicate payment execution
    if payment.status in ["COMPLETED", "PAID"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment #{payment.payment_reference} has already been settled on {payment.payment_date}.",
        )

    payment.status = "COMPLETED"
    payment.payment_date = date.today()

    invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
    if invoice:
        # Re-compute total settled balance
        balance_info = _calculate_invoice_balance(invoice, db)
        if balance_info["is_fully_paid"]:
            invoice.payment_status = "PAID"
        else:
            invoice.payment_status = "PARTIAL"

    audit = AuditLog(
        action="PAYMENT_SIMULATED_SETTLED",
        entity_type="PAYMENT",
        entity_id=str(payment.id),
        old_values={"status": "SCHEDULED"},
        new_values={
            "status": "COMPLETED",
            "payment_date": str(payment.payment_date),
            "invoice_payment_status": invoice.payment_status if invoice else "UNKNOWN",
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(payment)
    return payment
