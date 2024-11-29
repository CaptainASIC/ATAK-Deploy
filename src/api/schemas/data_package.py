from datetime import datetime
from typing import Optional
from pydantic import BaseModel, constr, validator

class DataPackageBase(BaseModel):
    """Base data package schema."""
    name: constr(min_length=1, max_length=255)
    package_type: constr(regex='^(full|basic|itak)$')
    server_config: dict
    manifest_config: dict

class DataPackageCreate(DataPackageBase):
    """Schema for data package creation."""
    certificate_id: int

    @validator('server_config')
    def validate_server_config(cls, v):
        """Validate server configuration."""
        required_fields = ['hostname', 'port', 'protocol']
        if not all(field in v for field in required_fields):
            raise ValueError(f"Server config must contain: {', '.join(required_fields)}")
        return v

    @validator('manifest_config')
    def validate_manifest_config(cls, v):
        """Validate manifest configuration."""
        required_fields = ['uid', 'version', 'name']
        if not all(field in v for field in required_fields):
            raise ValueError(f"Manifest config must contain: {', '.join(required_fields)}")
        return v

class DataPackageUpdate(BaseModel):
    """Schema for data package updates."""
    is_active: Optional[bool] = None
    server_config: Optional[dict] = None
    manifest_config: Optional[dict] = None

    @validator('server_config')
    def validate_server_config(cls, v):
        """Validate server configuration."""
        if v is not None:
            required_fields = ['hostname', 'port', 'protocol']
            if not all(field in v for field in required_fields):
                raise ValueError(f"Server config must contain: {', '.join(required_fields)}")
        return v

    @validator('manifest_config')
    def validate_manifest_config(cls, v):
        """Validate manifest configuration."""
        if v is not None:
            required_fields = ['uid', 'version', 'name']
            if not all(field in v for field in required_fields):
                raise ValueError(f"Manifest config must contain: {', '.join(required_fields)}")
        return v

class DataPackageResponse(DataPackageBase):
    """Schema for data package responses."""
    id: int
    file_path: str
    is_active: bool
    user_id: int
    certificate_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        """Pydantic config for ORM mode."""
        from_attributes = True

class DataPackageWithRelations(DataPackageResponse):
    """Schema for data package with related data."""
    user_username: str
    certificate_name: str
    certificate_type: str

    class Config:
        """Pydantic config for ORM mode."""
        from_attributes = True
