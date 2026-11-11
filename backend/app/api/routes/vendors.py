from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.vendor import Vendor
from app.schemas.vendor import VendorCreate, VendorResponse, VendorUpdate

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.get("", response_model=List[VendorResponse])
def list_vendors(
    search: Optional[str] = Query(None, description="Search by vendor name or code"),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List vendors with optional search and active status filters."""
    query = db.query(Vendor)
    if is_active is not None:
        query = query.filter(Vendor.is_active == is_active)
    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Vendor.legal_name.ilike(search_fmt),
                Vendor.vendor_code.ilike(search_fmt),
                Vendor.tax_identifier.ilike(search_fmt),
            )
        )
    return query.order_by(Vendor.legal_name).offset(skip).limit(limit).all()


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(vendor_id: int, db: Session = Depends(get_db)):
    """Get vendor details by ID."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(vendor_in: VendorCreate, db: Session = Depends(get_db)):
    """Register a new vendor."""
    existing = db.query(Vendor).filter(Vendor.vendor_code == vendor_in.vendor_code).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Vendor code '{vendor_in.vendor_code}' already exists")

    vendor = Vendor(
        vendor_code=vendor_in.vendor_code,
        legal_name=vendor_in.legal_name,
        contact_person=vendor_in.contact_person,
        email=vendor_in.email,
        phone=vendor_in.phone,
        address=vendor_in.address,
        tax_identifier=vendor_in.tax_identifier,
        bank_account_last_four=vendor_in.bank_account_last_four,
        bank_name=vendor_in.bank_name,
        is_active=vendor_in.is_active,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor

