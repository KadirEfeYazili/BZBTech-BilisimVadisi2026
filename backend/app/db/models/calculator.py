"""Hesaplayıcı envanteri ve sorgu kayıtları.

NEDEN ENVANTER AYRI BİR TABLO: Bazı bankalarda kâr payı oranı statik HTML'de
hiç yok; yalnızca bir hesaplama aracının içinde. Ziraat Katılım'da 16 seçenekli
bir finansman tipi dropdown'ı var ve o 16 seçenek ASLINDA 16 ÜRÜN VARYANTIDIR.
Yani hesaplayıcı sayfası, sorgulanmasa bile başlı başına bir veri kaynağıdır:
girdi alanları okunduğunda ürün varyantları, tutar limitleri ve izinli vadeler
çıkar.

Bu yüzden iki aşama ayrı tutulur:
  - `calculator_inventory` — sayfanın NE SUNDUĞU (girdi alanları, mekanizma,
    kaç kombinasyon olduğu, örneklemenin uygulanabilir olup olmadığı)
  - `calculator_probes` — fiilen YAPILAN her sorgu ve dönen değerler

⚠️ BAĞLAYICILIK: Hesaplayıcıdan dönen değerler bankanın taahhüdü DEĞİLDİR;
sayfalarda "bilgilendirme amaçlıdır" kaydı bulunur. `is_binding=False`
varsayılandır ve arayüzde rozetle gösterilir.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.vocab import CALCULATOR_MECHANISMS, PROBE_METHODS, SAMPLING_DECISIONS
from app.db.base import Base, TimestampMixin, UtcDateTime, in_check, utc_now

if TYPE_CHECKING:
    from app.db.models.bank import Bank
    from app.db.models.product import Product


class CalculatorInventory(TimestampMixin, Base):
    """Bir bankanın hesaplama aracının yapısal envanteri.

    ⚠️ Katılım terminolojisi: `total_combinations` kullanılır."""
    
    __tablename__ = "calculator_inventory"
    __table_args__ = (
        # Aynı sayfa iki kez envanterlenmez; yeniden incelemede kayıt güncellenir.
        UniqueConstraint("bank_id", "page_url", name="uq_calculator_inventory_bank_id_page_url"),
        CheckConstraint(in_check("mechanism", CALCULATOR_MECHANISMS), name="mechanism_valid"),
        CheckConstraint(
            in_check("sampling_decision", SAMPLING_DECISIONS), name="sampling_decision_valid"
        ),
        CheckConstraint(
            "amount_min IS NULL OR amount_max IS NULL OR amount_min <= amount_max",
            name="amount_range_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(
        ForeignKey("banks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_url: Mapped[str] = mapped_column(Text, nullable=False)
    calculator_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Girdi alanlarının ham yapısı. Örnek:
    # {"finansman_tipi": {"type": "select",
    #                     "options": [{"value": "1", "label": "Sıfır Konut"}, ...]},
    #  "tutar": {"type": "range", "min": 50000, "max": 5000000, "step": 1000},
    #  "vade":  {"type": "select", "options": [12, 24, 36, 48, 60]}}
    input_fields: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # Dropdown'daki seçenek sayısı = keşfedilen ürün varyantı sayısı.
    variant_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount_min: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    amount_max: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    allowed_terms: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)

    # Hesaplama nerede yapılıyor: sunucuda (api) mı, tarayıcıda mı?
    mechanism: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    endpoint_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    endpoint_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_template: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    response_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # varyant × tutar × vade kombinasyon sayısı. Bu sayı örnekleme kararını
    # belirler: on binlerce kombinasyon için tam tarama etik değildir.
    total_combinations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sampling_decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    feasible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Sayfada geçen "bilgilendirme amaçlıdır" ifadesi birebir saklanır.
    non_binding_notice: Mapped[str | None] = mapped_column(Text, nullable=True)

    inspected_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utc_now)

    bank: Mapped[Bank] = relationship(back_populates="calculator_inventories")
    probes: Mapped[list[CalculatorProbe]] = relationship(
        back_populates="inventory", cascade="all, delete-orphan"
    )


class CalculatorProbe(TimestampMixin, Base):
    """Hesaplayıcıya yapılmış tek bir sorgu ve dönen değerler.

    ⚠️ Katılım terminolojisi: `total_profit_share` kullanılır.
    """

    __tablename__ = "calculator_probes"
    __table_args__ = (
        # Aynı ürün/tutar/vade/varyant için tek kayıt: tekrar çalıştırmada
        # bankaya gereksiz istek atılmasını ve kayıt çoğalmasını engeller.
        UniqueConstraint(
            "product_id",
            "probe_amount",
            "probe_term_months",
            "probe_variant",
            name="uq_calculator_probes_product_id_probe_amount",
        ),
        CheckConstraint(in_check("method", PROBE_METHODS), name="method_valid"),
        CheckConstraint("probe_amount > 0", name="probe_amount_positive"),
        CheckConstraint("probe_term_months > 0", name="probe_term_months_positive"),
        Index("ix_calculator_probes_bank_id_product_id", "bank_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank_id: Mapped[int] = mapped_column(
        ForeignKey("banks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inventory_id: Mapped[int | None] = mapped_column(
        ForeignKey("calculator_inventory.id", ondelete="SET NULL"), nullable=True
    )

    # ── Sorgu girdisi ─────────────────────────────────────
    probe_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    probe_term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    probe_variant: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Sorgu çıktısı ─────────────────────────────────────
    profit_rate_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    monthly_installment: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    total_repayment: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    total_profit_share: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    allocation_fee: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    insurance_fee: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    annual_cost_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # ── Kanıt ─────────────────────────────────────────────
    method: Mapped[str] = mapped_column(Text, nullable=False)
    endpoint_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Ham yanıt saklanır: ayrıştırma sonradan düzeltilebilsin diye.
    response_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    probed_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, default=utc_now)
    # Varsayılan False: hesaplayıcı çıktısı bankanın taahhüdü değildir.
    is_binding: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    product: Mapped[Product] = relationship(back_populates="probes")
    bank: Mapped[Bank] = relationship(back_populates="calculator_probes")
    inventory: Mapped[CalculatorInventory | None] = relationship(back_populates="probes")
