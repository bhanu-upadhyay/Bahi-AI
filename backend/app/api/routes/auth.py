import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_user_optional
from app.core.security import create_access_token, verify_password
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse

logger = logging.getLogger("bahi_ai.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    req: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticates a university user with email and password,
    returning a signed JWT bearer token with role claims.
    """
    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user:
        logger.warning(f"Failed login attempt: user '{req.email}' not found.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(f"Login rejected: user '{req.email}' is deactivated.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact University IT Administration.",
        )

    if not verify_password(req.password, user.password_hash):
        logger.warning(f"Failed login attempt for user '{req.email}': invalid password.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate signed JWT token
    access_token = create_access_token(
        subject=user.email,
        role=user.role,
    )

    # Audit log login event
    try:
        audit = AuditLog(
            action="USER_LOGIN_SUCCESS",
            entity_type="USER",
            entity_id=str(user.id),
            user_id=user.id,
            new_values={"email": user.email, "role": user.role},
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not write login audit log: {e}")

    logger.info(f"User {user.email} successfully logged in as {user.role}.")
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Returns the authenticated user's profile and active permissions."""
    return UserResponse.model_validate(current_user)


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Terminates session and records logout in system audit trail."""
    if current_user:
        try:
            audit = AuditLog(
                action="USER_LOGOUT",
                entity_type="USER",
                entity_id=str(current_user.id),
                user_id=current_user.id,
                new_values={"email": current_user.email},
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            logger.warning(f"Could not write logout audit log: {e}")

    return {"message": "Session successfully terminated."}

