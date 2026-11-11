from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.budget import Budget
from app.schemas.budget import BudgetResponse

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.get("", response_model=List[BudgetResponse])
def list_budgets(
    fiscal_year: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """List department budgets with allocated, committed, spent, and available balances."""
    query = db.query(Budget).options(joinedload(Budget.department))
    if fiscal_year:
        query = query.filter(Budget.fiscal_year == fiscal_year)
    if department_id:
        query = query.filter(Budget.department_id == department_id)

    return query.order_by(Budget.department_id).all()


@router.get("/{budget_id}", response_model=BudgetResponse)
def get_budget(budget_id: int, db: Session = Depends(get_db)):
    """Get single department budget."""
    budget = db.query(Budget).options(joinedload(Budget.department)).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget record not found")
    return budget

