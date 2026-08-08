"""Terminoloji sözlüğü — KATILIM BANKACILIĞI KAVRAMLARI.

Şartname 5.5'in karşılığıdır. İki tür kayıt tutar:
  1. Katılım bankacılığı terimi + konvansiyonel karşılığı (ör. Kâr Payı Oranı ↔ faiz oranı)
  2. `is_forbidden_conventional=True` ile işaretli YASAKLI konvansiyonel terimler
     (faiz, kredi, mevduat ...) — bu satırlarda `conventional_equivalent` alanı,
     kullanılması gereken katılım karşılığını taşır.

PART 3'teki terminoloji koruması (terminology_guard) bu tabloyu kullanacaktır.
"""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class GlossaryTerm(Base, TimestampMixin):
    """Tek bir terminoloji kaydı."""

    __tablename__ = "glossary"

    id: Mapped[int] = mapped_column(primary_key=True)

    term: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Yasaklı olmayan kayıtlarda: konvansiyonel bankacılıktaki karşılığı.
    # Yasaklı kayıtlarda: kullanılması gereken katılım bankacılığı karşılığı.
    conventional_equivalent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Ör. oran, hesap, ucret, vade, urun
    category: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)

    # Metinde geçebilecek eş yazımlar: ["kar payi orani", "kâr payı oranı"]
    aliases: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # True ise bu terim konvansiyoneldir ve üretilen metinlerde KULLANILMAZ.
    is_forbidden_conventional: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
