"""Kazıma çalıştırması kaydı — izlenebilirlik ve hata raporu."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Final

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UtcDateTime, utc_now

if TYPE_CHECKING:
    from app.db.models.bank import Bank

# Çalıştırma sonucu.
#   partial — bazı URL'lerde hata oluştu ama çalıştırma tamamlandı.
#             Tek bir URL hatası TÜM çalıştırmayı durdurmaz (§12).
SCRAPE_RUN_STATUSES: Final[tuple[str, ...]] = ("running", "success", "partial", "failed")


class ScrapeRun(Base):
    """Bir bankanın tek bir kazıma çalıştırmasının özeti."""

    __tablename__ = "scrape_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'success', 'partial', 'failed')",
            name="status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(
        ForeignKey("banks.id", ondelete="CASCADE"), nullable=False, index=True
    )

    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="running", index=True)

    urls_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    urls_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    campaigns_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    campaigns_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Hata özetleri satır satır biriktirilir; ham HTML zaten arşivde durur.
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    scraper_version: Mapped[str | None] = mapped_column(Text, nullable=True)

    bank: Mapped[Bank] = relationship(back_populates="scrape_runs")
