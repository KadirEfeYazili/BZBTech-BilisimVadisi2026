"""Kampanya metrikleri — normalize edilmiş sayısal alanlar.

Şartname 5.3'teki her finansal alan burada birebir bir kolona karşılık gelir.
PART 1'de tablo OLUŞTURULUR ama DOLDURULMAZ; doldurma mantığı PART 3'te gelir.

KURAL: Para ve oran alanlarının tamamı `Numeric` (Decimal) — `Float` yasak.
Kayan noktalı sayı finansal değerde yuvarlama hatası üretir.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.campaign import Campaign


class CampaignMetric(Base):
    """Bir kampanyanın yapılandırılmış finansal değerleri.

    Tüm alanlar nullable: bankaların hiçbirinde tüm alanlar aynı anda bulunmuyor.
    """

    __tablename__ = "campaign_metrics"

    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )

    # ── Kâr payı / oranlar (faiz DEĞİL — katılım bankacılığı terminolojisi) ──
    profit_rate_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    profit_share_rate_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # ── Vade ve taksit ────────────────────────────────────
    term_months_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    term_months_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    installment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Finansman tutarı ──────────────────────────────────
    financing_amount_min: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    financing_amount_max: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)

    # ── Harcama eşikleri ve ödül ──────────────────────────
    min_spend_try: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    max_spend_try: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    reward_amount_try: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    reward_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    cashback_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    discount_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    loyalty_points: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)

    # ── Masraf ve ücretler ────────────────────────────────
    allocation_fee_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    file_fee_try: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    has_no_fee: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    appraisal_fee_covered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # ── Toplam fayda üst sınırı ───────────────────────────
    max_total_benefit_try: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)

    # Kademeli ödül yapısı: [{"threshold": 5000, "reward": 250}, ...]
    tier_structure: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    currency: Mapped[str | None] = mapped_column(Text, nullable=True, default="TRY")

    campaign: Mapped[Campaign] = relationship(back_populates="metric")
