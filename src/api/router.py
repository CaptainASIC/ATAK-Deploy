from fastapi import APIRouter
from .v1 import users, certificates, data_packages, auth

# Create the main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

api_router.include_router(
    certificates.router,
    prefix="/certificates",
    tags=["Certificates"]
)

api_router.include_router(
    data_packages.router,
    prefix="/data-packages",
    tags=["Data Packages"]
)
