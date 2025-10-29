"""API v1 router aggregator."""

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router

# Create v1 API router
router = APIRouter()

# Include all v1 sub-routers
router.include_router(auth_router)
router.include_router(admin_router)
