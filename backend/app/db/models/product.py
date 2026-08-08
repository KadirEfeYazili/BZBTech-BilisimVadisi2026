"""Ürün ve ürün oranı modelleri.

PART 1'de tablolar OLUŞTURULUR ama DOLDURULMAZ; ürün kazıma PART 2'de gelir.
Terminoloji: "finansman" kullanılır, konvansiyonel karşılığı KULLANILMAZ.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.bank import Bank
    from app.db.models.source_document import SourceDocument


class Product(TimestampMixin, Base):
    """Bankanın sürekli sunduğu finansal ürün (kampanya değil)."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(
        ForeignKey("banks.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Ör. konut_finansmani, tasit_finansmani, katilma_hesabi, kart
    product_type: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    segment: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True
    )

    bank: Mapped[Bank] = relationship(back_populates="products")
    source_document: Mapped[SourceDocument | None] = relationship()
    rates: Mapped[list[ProductRate]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductRate(Base):
    """Bir ürünün vadeye göre kâr payı oranı ve maliyet satırı.

    Kaynak: bankaların ürün sayfalarındaki HTML oran tabloları
    (ör. Vade | Kâr Payı Oranı | Tahsis Ücreti | Aylık/Yıllık Toplam Maliyet).
    """

    __tablename__ = "product_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )

    term_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profit_rate_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    allocation_fee_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    monthly_cost_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    annual_cost_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # Aynı sayfada birden fazla tablo olabilir (ör. sigortalı / sigortasız).
    variant: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    product: Mapped[Product] = relationship(back_populates="rates")
