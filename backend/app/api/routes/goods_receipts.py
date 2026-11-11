from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.goods_receipt import GoodsReceipt
from app.schemas.goods_receipt import GoodsReceiptResponse

router = APIRouter(prefix="/goods-receipts", tags=["Goods Receipts"])


@router.get("", response_model=List[GoodsReceiptResponse])
def list_goods_receipts(
    purchase_order_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List goods receipt notes with line items and receiving officer."""
    query = (
        db.query(GoodsReceipt)
        .options(
            joinedload(GoodsReceipt.lines),
            joinedload(GoodsReceipt.receiver),
        )
    )

    if purchase_order_id:
        query = query.filter(GoodsReceipt.purchase_order_id == purchase_order_id)
    if status:
        query = query.filter(GoodsReceipt.status == status.upper())

    return query.order_by(GoodsReceipt.received_date.desc()).offset(skip).limit(limit).all()


@router.get("/{grn_id}", response_model=GoodsReceiptResponse)
def get_goods_receipt(grn_id: int, db: Session = Depends(get_db)):
    """Get single goods receipt note details."""
    grn = (
        db.query(GoodsReceipt)
        .options(
            joinedload(GoodsReceipt.lines),
            joinedload(GoodsReceipt.receiver),
        )
        .filter(GoodsReceipt.id == grn_id)
        .first()
    )
    if not grn:
        raise HTTPException(status_code=404, detail="Goods receipt not found")
    return grn

