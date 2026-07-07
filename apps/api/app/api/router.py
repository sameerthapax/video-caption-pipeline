from fastapi import APIRouter

from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.health import router as health_router
from app.api.endpoints.jobs import router as jobs_router
from app.api.endpoints.videos import router as videos_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/api/auth", tags=["auth"])
api_router.include_router(videos_router, prefix="/api/videos", tags=["videos"])
api_router.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"])
