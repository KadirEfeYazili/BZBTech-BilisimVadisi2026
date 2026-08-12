"""Kampanya taksonomisi — çok eksenli, çok etiketli sınıflandırma.

NEDEN `campaigns.category` TEK BAŞINA YETMİYOR: Tek eksenli bir kategori alanı
"Migros'ta market alışverişine taksit" kampanyasını ya ürün türüne (kart) ya da
sektöre (market) göre etiketlemek zorunda bırakır; ikisi birden gerekli.
Şartname 5.4 kampanya türünün belirlenmesini istiyor, ama karşılaştırma ve
SPRINT 5'teki arama için dört DİK eksen gerekiyor:

    product_type — şartnamenin 8 zorunlu ürün türü
    sector       — harcamanın yapıldığı sektör (22 sektör)
    audience     — hedef kitle (yeni müşteri, emekli, esnaf ...)
    benefit      — fayda türü (taksit, puan, indirim, masrafsızlık ...)

Bir kampanya her eksende BİRDEN FAZLA etiket alabilir; bu yüzden etiketler
`campaigns` üzerinde sütun değil, ayrı satırlardır.

Her etiket kanıtıyla saklanır: hangi kaynaktan (`source`) ve hangi metinden
(`evidence`) çıkarıldığı yazılır. Kaynaksız etiket, SPRINT 3'teki F1 ölçümünde
hatanın nereden geldiğini bulmayı imkânsızlaştırır.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.vocab import CATEGORY_SOURCES, TAXONOMY_AXES
from app.db.base import Base, TimestampMixin, in_check

if TYPE_CHECKING:
    from app.db.models.campaign import Campaign


class CampaignCategory(TimestampMixin, Base):
    """Bir kampanyanın tek bir eksendeki tek bir etiketi."""

    __tablename__ = "campaign_categories"
    __table_args__ = (
        # Aynı kampanyaya aynı eksende aynı etiket iki kez yazılmaz.
        # Sınıflandırıcı tekrar çalıştırıldığında kayıt çoğalmasın diye
        # upsert anahtarı budur.
        UniqueConstraint(
            "campaign_id", "axis", "value", name="uq_campaign_categories_campaign_id_axis_value"
        ),
        CheckConstraint(in_check("axis", TAXONOMY_AXES), name="axis_valid"),
        CheckConstraint(in_check("source", CATEGORY_SOURCES), name="source_valid"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range_valid"),
        Index("ix_campaign_categories_axis_value", "axis", "value"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )

    axis: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, default=Decimal("1.000")
    )
    # ⚠️ `llm` SPRINT 3'te doldurulacak. SPRINT 2'de üretilen etiketlerin
    # kaynağı yalnızca url | bank_category | keyword | merchant olabilir —
    # bu sprintteki sınıflandırma tamamen kural tabanlı ve deterministiktir.
    source: Mapped[str] = mapped_column(Text, nullable=False)
    # Etiketin dayandığı ham metin parçası veya URL bileşeni.
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped[Campaign] = relationship(back_populates="categories")
