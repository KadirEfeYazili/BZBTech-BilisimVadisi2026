"""API v1 yönlendirici birleştirme."""

from fastapi import APIRouter

from app.api.v1 import banks, campaigns, health, stats

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(banks.router)
api_router.include_router(campaigns.router)
api_router.include_router(stats.router)

__all__ = ["api_router"]
