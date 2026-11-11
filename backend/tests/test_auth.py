import pytest
from app.core.security import get_password_hash, verify_password, create_access_token
import jwt
from app.core.config import settings


def test_password_hashing():
    pwd = "UniversityAP@2025!"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_jwt_token_generation():
    token = create_access_token(subject="sarah.jenkins@university.edu", role="FINANCE_ADMIN")
    assert isinstance(token, str)
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded["sub"] == "sarah.jenkins@university.edu"
    assert decoded["role"] == "FINANCE_ADMIN"

