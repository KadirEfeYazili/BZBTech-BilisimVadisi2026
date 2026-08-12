"""Banka modeli — BDDK/TKBB listesindeki katılım bankaları."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from sqlalchemy import JSON, Boolean, CheckConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.calculator import CalculatorInventory, CalculatorProbe
    from app.db.models.campaign import Campaign
    from app.db.models.product import Product
    from app.db.models.scrape_run import ScrapeRun
    from app.db.models.source_document import SourceDocument

# BDDK faaliyet izni durumu
BDDK_STATUSES: Final[tuple[str, ...]] = ("active", "pre_launch")

# Kamuya açık veri zenginliği: rich = kampanya/ürün sayfası var,
# limited = az sayıda veya eksik alanlı, none = kamuya açık kampanya sayfası yok.
DATA_STATUSES: Final[tuple[str, ...]] = ("rich", "limited", "none")


class Bank(TimestampMixin, Base):
    """Katılım bankası kaydı.

    Şartname 5.1 gereği BDDK listesindeki bankaların *tümü* bulunur; kamuya açık
    kampanyası olmayan bankalar da (`data_status='none'`) sistemde açıkça durur.
    """

    __tablename__ = "banks"
    __table_args__ = (
        CheckConstraint(
            "bddk_status IN ('active', 'pre_launch')",
            name="bddk_status_valid",
        ),
        CheckConstraint(
            "data_status IN ('rich', 'limited', 'none')",
            name="data_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Scraper kayıt anahtarı: kuveyt_turk, emlak_katilim ...
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    legal_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str] = mapped_column(Text, nullable=False)

    # Eski/yönlendirilen alan adları: ["albarakaturk.com.tr"]
    # Scraper cross-host yönlendirmeyi takip eder, bu liste belgeleme amaçlıdır.
    legacy_domains: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    bddk_status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    tkbb_member: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    data_status: Mapped[str] = mapped_column(Text, nullable=False, default="rich")

    brand_color: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Veri durumunun gerekçesi (ör. "faaliyet izni 26.02.2026, site henüz açılmadı")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaigns: Mapped[list[Campaign]] = relationship(
        back_populates="bank", cascade="all, delete-orphan"
    )
    source_documents: Mapped[list[SourceDocument]] = relationship(
        back_populates="bank", cascade="all, delete-orphan"
    )
    products: Mapped[list[Product]] = relationship(
        back_populates="bank", cascade="all, delete-orphan"
    )
    scrape_runs: Mapped[list[ScrapeRun]] = relationship(
        back_populates="bank", cascade="all, delete-orphan"
    )
    calculator_inventories: Mapped[list[CalculatorInventory]] = relationship(
        back_populates="bank", cascade="all, delete-orphan"
    )
    calculator_probes: Mapped[list[CalculatorProbe]] = relationship(
        back_populates="bank", cascade="all, delete-orphan"
    )
