from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.payment import Payment
from app.models.invoice import Invoice
from app.models.audit_log import AuditLog
from app.schemas.payment import PaymentCreate, PaymentResponse

router = APIRouter(prefix="/payments", tags=["Payments"])


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
    return query.order_by(Payment.scheduled_date.desc()).offset(skip).limit(limit).all()


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    """Get single payment record details."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")
    return payment


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def schedule_payment(payment_in: PaymentCreate, db: Session = Depends(get_db)):
    """Schedule a new disbursement for an approved invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == payment_in.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

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
def simulate_payment_settlement(payment_id: int, db: Session = Depends(get_db)):
    """Simulate mock payment settlement and bank confirmation."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment.status = "COMPLETED"
    payment.payment_date = date.today()

    invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
    if invoice:
        invoice.payment_status = "PAID"

    audit = AuditLog(
        action="PAYMENT_SIMULATED_SETTLED",
        entity_type="PAYMENT",
        entity_id=str(payment.id),
        old_values={"status": "SCHEDULED"},
        new_values={"status": "COMPLETED", "payment_date": str(payment.payment_date)},
    )
    db.add(audit)
    db.commit()
    db.refresh(payment)
    return payment

