from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from pwdlib import PasswordHash
import jwt
from app.core.config import settings

# Initialize password hasher with Argon2
password_hash_helper = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored hash."""
    return password_hash_helper.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hashes a password using the configured hasher."""
    return password_hash_helper.hash(password)


def create_access_token(subject: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": subject,
        "role": role,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

