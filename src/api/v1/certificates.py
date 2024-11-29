import os
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from ...db.session import get_db
from ...db.models import Certificate, User
from ..schemas.certificate import (
    CertificateCreate,
    CertificateUpdate,
    CertificateResponse,
    CertificateWithUser
)
from .auth import get_current_active_user
from ...config.settings import get_settings
from ...utils.certificate import generate_certificate, revoke_certificate

router = APIRouter()
settings = get_settings()

@router.post("/", response_model=CertificateResponse)
async def create_certificate(
    cert_data: CertificateCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new certificate."""
    # Generate certificate files
    try:
        cert_info = await generate_certificate(
            cert_type=cert_data.cert_type,
            name=cert_data.name,
            user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate certificate: {str(e)}"
        )

    # Create certificate record
    db_certificate = Certificate(
        name=cert_data.name,
        cert_type=cert_data.cert_type,
        file_path=cert_info["file_path"],
        expiration_date=datetime.utcnow() + timedelta(days=365),  # 1 year validity
        user_id=current_user.id
    )

    db.add(db_certificate)
    await db.commit()
    await db.refresh(db_certificate)

    return db_certificate

@router.get("/", response_model=List[CertificateWithUser])
async def list_certificates(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List certificates (filtered by user unless superuser)."""
    query = select(Certificate).join(User)
    
    if not current_user.is_superuser:
        query = query.filter(Certificate.user_id == current_user.id)
    
    result = await db.execute(
        query.offset(skip).limit(limit)
    )
    certificates = result.scalars().all()
    return certificates

@router.get("/{cert_id}", response_model=CertificateWithUser)
async def get_certificate(
    cert_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get certificate by ID."""
    result = await db.execute(
        select(Certificate)
        .join(User)
        .filter(Certificate.id == cert_id)
    )
    certificate = result.scalar_one_or_none()

    if certificate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    if not current_user.is_superuser and certificate.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    return certificate

@router.put("/{cert_id}", response_model=CertificateResponse)
async def update_certificate(
    cert_id: int,
    cert_update: CertificateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update certificate (mainly for revocation)."""
    # Get certificate
    result = await db.execute(
        select(Certificate).filter(Certificate.id == cert_id)
    )
    certificate = result.scalar_one_or_none()

    if certificate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    if not current_user.is_superuser and certificate.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Handle revocation
    if cert_update.is_revoked and not certificate.is_revoked:
        try:
            await revoke_certificate(certificate.file_path)
            cert_update.revocation_date = datetime.utcnow()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to revoke certificate: {str(e)}"
            )

    # Update certificate
    update_data = cert_update.dict(exclude_unset=True)
    await db.execute(
        update(Certificate)
        .where(Certificate.id == cert_id)
        .values(**update_data)
    )
    await db.commit()

    # Get updated certificate
    result = await db.execute(
        select(Certificate).filter(Certificate.id == cert_id)
    )
    updated_cert = result.scalar_one()
    return updated_cert

@router.get("/{cert_id}/download")
async def download_certificate(
    cert_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Download certificate files."""
    # Get certificate
    result = await db.execute(
        select(Certificate).filter(Certificate.id == cert_id)
    )
    certificate = result.scalar_one_or_none()

    if certificate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    if not current_user.is_superuser and certificate.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    if certificate.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Certificate is revoked"
        )

    # Check if certificate file exists
    if not os.path.exists(certificate.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file not found"
        )

    return {"file_path": certificate.file_path}

@router.post("/{cert_id}/revoke", response_model=CertificateResponse)
async def revoke_cert(
    cert_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke a certificate."""
    # Get certificate
    result = await db.execute(
        select(Certificate).filter(Certificate.id == cert_id)
    )
    certificate = result.scalar_one_or_none()

    if certificate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    if not current_user.is_superuser and certificate.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    if certificate.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Certificate is already revoked"
        )

    # Revoke certificate
    try:
        await revoke_certificate(certificate.file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke certificate: {str(e)}"
        )

    # Update certificate status
    await db.execute(
        update(Certificate)
        .where(Certificate.id == cert_id)
        .values(
            is_revoked=True,
            revocation_date=datetime.utcnow()
        )
    )
    await db.commit()

    # Get updated certificate
    result = await db.execute(
        select(Certificate).filter(Certificate.id == cert_id)
    )
    updated_cert = result.scalar_one()
    return updated_cert
