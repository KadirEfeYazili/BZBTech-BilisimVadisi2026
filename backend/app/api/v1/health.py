"""Sağlık denetimi ucu."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app import __version__
from app.api.deps import DbSession
from app.db.models import Campaign
from app.logging_config import get_logger
from app.schemas.common import HealthResponse

logger = get_logger(__name__)

router = APIRouter(tags=["sistem"])


@router.get("/health", response_model=HealthResponse, summary="Sistem sağlığı")
def health(session: DbSession) -> HealthResponse:
    """Uygulamanın ve veritabanı bağlantısının durumunu döndürür.

    Veritabanına erişilemese bile 200 döner; sorun `db_ok=false` ile bildirilir.
    Böylece izleme araçları uygulamanın ayakta olduğunu ancak veritabanının
    erişilemez olduğunu ayırt edebilir.
    """
    db_ok = True
    campaign_count = 0

    try:
        campaign_count = session.scalar(select(func.count()).select_from(Campaign)) or 0
    except Exception as exc:
        db_ok = False
        logger.error("saglik_denetimi_db_hatasi", hata=str(exc))

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version=__version__,
        db_ok=db_ok,
        campaign_count=campaign_count,
    )
