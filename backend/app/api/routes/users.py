from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """List system users for role switching and demonstration."""
    return db.query(User).order_by(User.id).all()

