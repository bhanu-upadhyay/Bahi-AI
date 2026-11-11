from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    full_name: str = Field(..., max_length=150)
    email: EmailStr
    role: str
    department_id: Optional[int] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

