"""İstatistik ucu."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.stats import StatsResponse
from app.services.stats_service import get_stats

router = APIRouter(prefix="/stats", tags=["istatistik"])


@router.get("", response_model=StatsResponse, summary="Gösterge paneli istatistikleri")
def read_stats(session: DbSession) -> StatsResponse:
    """Genel bakış sayfasının beslendiği toplu sayıları döndürür.

    `unknown_status_campaigns` ayrı bir sayaçtır ve `expired` ile
    BİRLEŞTİRİLMEZ: tarihi bulunamayan kampanyayı süresi dolmuş göstermek
    yanlış bilgi olurdu.
    """
    return get_stats(session)
