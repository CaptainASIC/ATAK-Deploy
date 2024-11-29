from datetime import datetime
from typing import Any
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declared_attr

from .session import Base

class TimestampMixin:
    """Mixin for adding created_at and updated_at timestamps."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class BaseModel(Base):
    """Abstract base model with common attributes."""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

class User(TimestampMixin, BaseModel):
    """User model for authentication and tracking."""
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Relationships
    certificates = relationship("Certificate", back_populates="user")
    data_packages = relationship("DataPackage", back_populates="user")

class Certificate(TimestampMixin, BaseModel):
    """Certificate management model."""
    name = Column(String, nullable=False)
    cert_type = Column(String, nullable=False)  # client, server, ca
    file_path = Column(String, nullable=False)
    expiration_date = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    revocation_date = Column(DateTime(timezone=True), nullable=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("user.id"))
    
    # Relationships
    user = relationship("User", back_populates="certificates")
    data_packages = relationship("DataPackage", back_populates="certificate")

class DataPackage(TimestampMixin, BaseModel):
    """Data package model for managing ATAK configurations."""
    name = Column(String, nullable=False)
    package_type = Column(String, nullable=False)  # full, basic, itak
    file_path = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Configuration fields
    server_config = Column(String, nullable=False)  # JSON string of server configuration
    manifest_config = Column(String, nullable=False)  # JSON string of manifest configuration
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("user.id"))
    certificate_id = Column(Integer, ForeignKey("certificate.id"))
    
    # Relationships
    user = relationship("User", back_populates="data_packages")
    certificate = relationship("Certificate", back_populates="data_packages")

class AuditLog(TimestampMixin, BaseModel):
    """Audit log for tracking system activities."""
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"))
    details = Column(String, nullable=True)  # JSON string of additional details
    
    # Relationships
    user = relationship("User")
