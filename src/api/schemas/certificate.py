from datetime import datetime
from typing import Optional
from pydantic import BaseModel, constr

class CertificateBase(BaseModel):
    """Base certificate schema."""
    name: constr(min_length=1, max_length=255)
    cert_type: constr(regex='^(client|server|ca)$')

class CertificateCreate(CertificateBase):
    """Schema for certificate creation."""
    pass

class CertificateUpdate(BaseModel):
    """Schema for certificate updates."""
    is_revoked: Optional[bool] = None
    revocation_date: Optional[datetime] = None

class CertificateResponse(CertificateBase):
    """Schema for certificate responses."""
    id: int
    file_path: str
    expiration_date: datetime
    is_revoked: bool
    revocation_date: Optional[datetime]
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        """Pydantic config for ORM mode."""
        from_attributes = True

class CertificateWithUser(CertificateResponse):
    """Schema for certificate with user details."""
    user_username: str
    user_email: str

    class Config:
        """Pydantic config for ORM mode."""
        from_attributes = True
