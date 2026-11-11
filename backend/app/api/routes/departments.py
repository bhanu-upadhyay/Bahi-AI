from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentResponse

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=List[DepartmentResponse])
def list_departments(db: Session = Depends(get_db)):
    """List all active departments."""
    return db.query(Department).filter(Department.is_active == True).order_by(Department.name).all()


@router.get("/{dept_id}", response_model=DepartmentResponse)
def get_department(dept_id: int, db: Session = Depends(get_db)):
    """Get single department details."""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(dept_in: DepartmentCreate, db: Session = Depends(get_db)):
    """Register a new department."""
    existing = db.query(Department).filter(Department.code == dept_in.code).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Department code '{dept_in.code}' already exists")

    dept = Department(
        name=dept_in.name,
        code=dept_in.code,
        description=dept_in.description,
        is_active=dept_in.is_active,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept

