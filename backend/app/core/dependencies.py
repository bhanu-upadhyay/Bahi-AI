from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

security = HTTPBearer(auto_error=False)


def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Retrieves current user if JWT token is provided."""
    if not auth:
        return None
    try:
        payload = jwt.decode(auth.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            return None
        user = db.query(User).filter(User.email == email).first()
        return user
    except Exception:
        return None


def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """Enforces authentication if required."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

