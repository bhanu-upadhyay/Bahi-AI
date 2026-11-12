from typing import Callable, Generator, List, Optional, Sequence
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

security = HTTPBearer(auto_error=False)

# Standard Role Constants
ROLE_FINANCE_ADMIN = "FINANCE_ADMIN"
ROLE_FINANCE_OFFICER = "FINANCE_OFFICER"
ROLE_PROCUREMENT_OFFICER = "PROCUREMENT_OFFICER"
ROLE_HOD = "HOD"
ROLE_VENDOR = "VENDOR"

FINANCE_ROLES = (ROLE_FINANCE_ADMIN, ROLE_FINANCE_OFFICER)
APPROVAL_ROLES = (ROLE_FINANCE_ADMIN, ROLE_FINANCE_OFFICER, ROLE_HOD)


def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Retrieves current user if JWT token is provided.
    Validates token signature, expiration, and user active status.
    """
    if not auth or not auth.credentials:
        return None
    try:
        payload = jwt.decode(
            auth.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        email: Optional[str] = payload.get("sub")
        if not email:
            return None
        user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        return None


def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """Enforces authentication; raises 401 if missing or invalid."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or are invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*allowed_roles: str) -> Callable[[Optional[User]], Optional[User]]:
    """Dependency factory enforcing Role-Based Access Control (RBAC).
    If a user is authenticated, their role MUST match one of `allowed_roles`.
    """
    def role_verifier(
        user: Optional[User] = Depends(get_current_user_optional),
    ) -> Optional[User]:
        if user is not None:
            if user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Access forbidden: User role '{user.role}' is not authorized for this operation. "
                        f"Required roles: {', '.join(allowed_roles)}."
                    ),
                )
        return user

    return role_verifier
