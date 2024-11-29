from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from ...db.session import get_db
from ...db.models import DataPackage, User, Certificate
from ..schemas.data_package import (
    DataPackageCreate,
    DataPackageUpdate,
    DataPackageResponse,
    DataPackageWithRelations
)
from .auth import get_current_active_user
from ...utils.data_package import create_data_package_files, update_data_package_files

router = APIRouter()

@router.post("/", response_model=DataPackageResponse)
async def create_data_package(
    package_data: DataPackageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new data package."""
    # Verify certificate exists and belongs to user
    result = await db.execute(
        select(Certificate)
        .filter(Certificate.id == package_data.certificate_id)
    )
    certificate = result.scalar_one_or_none()

    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    if certificate.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Certificate does not belong to user"
        )

    if certificate.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot use revoked certificate"
        )

    try:
        # Generate data package files
        file_path = await create_data_package_files(
            package_type=package_data.package_type,
            server_config=package_data.server_config,
            manifest_config=package_data.manifest_config,
            certificate=certificate,
            user=current_user
        )

        # Create database record
        db_package = DataPackage(
            name=package_data.name,
            package_type=package_data.package_type,
            file_path=file_path,
            server_config=package_data.server_config,
            manifest_config=package_data.manifest_config,
            user_id=current_user.id,
            certificate_id=certificate.id
        )

        db.add(db_package)
        await db.commit()
        await db.refresh(db_package)

        return db_package

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create data package: {str(e)}"
        )

@router.get("/", response_model=List[DataPackageWithRelations])
async def list_data_packages(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List data packages (filtered by user unless superuser)."""
    query = select(DataPackage).join(User).join(Certificate)
    
    if not current_user.is_superuser:
        query = query.filter(DataPackage.user_id == current_user.id)
    
    result = await db.execute(
        query.offset(skip).limit(limit)
    )
    packages = result.scalars().all()
    return packages

@router.get("/{package_id}", response_model=DataPackageWithRelations)
async def get_data_package(
    package_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get data package by ID."""
    result = await db.execute(
        select(DataPackage)
        .join(User)
        .join(Certificate)
        .filter(DataPackage.id == package_id)
    )
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data package not found"
        )

    if package.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    return package

@router.put("/{package_id}", response_model=DataPackageResponse)
async def update_data_package(
    package_id: int,
    package_update: DataPackageUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update data package."""
    # Get existing package
    result = await db.execute(
        select(DataPackage)
        .filter(DataPackage.id == package_id)
    )
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data package not found"
        )

    if package.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    try:
        # Update package files if configs changed
        if package_update.server_config or package_update.manifest_config:
            await update_data_package_files(
                package=package,
                server_config=package_update.server_config or package.server_config,
                manifest_config=package_update.manifest_config or package.manifest_config
            )

        # Update database record
        update_data = package_update.dict(exclude_unset=True)
        await db.execute(
            update(DataPackage)
            .where(DataPackage.id == package_id)
            .values(**update_data)
        )
        await db.commit()

        # Get updated package
        result = await db.execute(
            select(DataPackage).filter(DataPackage.id == package_id)
        )
        updated_package = result.scalar_one()
        return updated_package

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update data package: {str(e)}"
        )

@router.get("/{package_id}/download")
async def download_data_package(
    package_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Download data package files."""
    result = await db.execute(
        select(DataPackage)
        .filter(DataPackage.id == package_id)
    )
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data package not found"
        )

    if package.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    if not package.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data package is not active"
        )

    # Verify certificate is still valid
    result = await db.execute(
        select(Certificate)
        .filter(Certificate.id == package.certificate_id)
    )
    certificate = result.scalar_one()

    if certificate.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Associated certificate is revoked"
        )

    return {"file_path": package.file_path}
