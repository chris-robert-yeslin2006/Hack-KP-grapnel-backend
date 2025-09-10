from fastapi import APIRouter

from app.api.v1.endpoints import hashes, notifications, health,dashboard

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(hashes.router, prefix="/hashes", tags=["hashes"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])