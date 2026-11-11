from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.purchase_order import PurchaseOrder
from app.schemas.purchase_order import PurchaseOrderResponse

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])


@router.get("", response_model=List[PurchaseOrderResponse])
def list_purchase_orders(
    department_id: Optional[int] = Query(None),
    vendor_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List purchase orders with lines, department, and vendor info."""
    query = (
        db.query(PurchaseOrder)
        .options(
            joinedload(PurchaseOrder.vendor),
            joinedload(PurchaseOrder.department),
            joinedload(PurchaseOrder.lines),
        )
    )

    if department_id:
        query = query.filter(PurchaseOrder.department_id == department_id)
    if vendor_id:
        query = query.filter(PurchaseOrder.vendor_id == vendor_id)
    if status:
        query = query.filter(PurchaseOrder.status == status.upper())

    return query.order_by(PurchaseOrder.issue_date.desc()).offset(skip).limit(limit).all()


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
def get_purchase_order(po_id: int, db: Session = Depends(get_db)):
    """Get single purchase order details."""
    po = (
        db.query(PurchaseOrder)
        .options(
            joinedload(PurchaseOrder.vendor),
            joinedload(PurchaseOrder.department),
            joinedload(PurchaseOrder.lines),
        )
        .filter(PurchaseOrder.id == po_id)
        .first()
    )
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po

