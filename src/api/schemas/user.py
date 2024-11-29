from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, constr

class UserBase(BaseModel):
    """Base user schema with common attributes."""
    username: constr(min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    """Schema for user creation requests."""
    password: constr(min_length=8)

class UserUpdate(BaseModel):
    """Schema for user update requests."""
    email: Optional[EmailStr] = None
    password: Optional[constr(min_length=8)] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    """Schema for user responses."""
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        """Pydantic config for ORM mode."""
        from_attributes = True

class UserInDB(UserResponse):
    """Schema for user in database (includes hashed password)."""
    hashed_password: str

    class Config:
        """Pydantic config for ORM mode."""
        from_attributes = True
