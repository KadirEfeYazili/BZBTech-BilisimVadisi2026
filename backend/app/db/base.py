"""SQLAlchemy 2.0 deklaratif taban sınıfı ve ortak sütun tipleri.

PostgreSQL uyumluluk kuralları (§6.1) burada merkezileştirilir:
  - `String(n)` yerine `Text`
  - `DateTime(timezone=True)` — naive datetime yasak
  - Para/oran için `Numeric`, `Float` yasak
  - JSON alanları için `sqlalchemy.JSON` (SQLite'ta TEXT, PG'de JSONB'ye map olur)
  - Alembic'in PostgreSQL'de tutarlı kısıt adı üretmesi için naming convention
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, TypeDecorator
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Alembic'in ürettiği kısıt adlarının veritabanından bağımsız olarak aynı kalmasını sağlar.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utc_now() -> datetime:
    """Zaman dilimi bilgisi taşıyan şimdiki zamanı (UTC) döndürür.

    §11 gereği naive datetime üretilmez.
    """
    return datetime.now(UTC)


def in_check(column: str, values: tuple[str, ...]) -> str:
    """Kontrollü sözlük için `CheckConstraint` SQL ifadesi üretir.

    Değer listesini elle yazmak yerine `app/core/vocab.py`'deki sözlükten
    türetmek, sözlüğe eklenen bir değerin şemada unutulmasını engeller.

    Args:
        column: Kısıtlanacak sütun adı.
        values: İzin verilen değerler.

    Returns:
        `"column IN ('a', 'b')"` biçiminde SQL parçası.

    """
    listelenen = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({listelenen})"


class UtcDateTime(TypeDecorator[datetime]):
    """Her zaman UTC'ye demirlenmiş, zaman dilimi bilgili datetime sütunu.

    Gerekçe: SQLite zaman dilimi bilgisini saklamaz ve okurken naive datetime
    döndürür. Bu tip, yazarken değeri UTC'ye çevirir, okurken zaman dilimini
    geri ekler. Böylece SQLite ve PostgreSQL aynı davranışı gösterir ve
    API'den dönen tarihlerde zaman dilimi kayması oluşmaz.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        """Veritabanına yazmadan önce değeri UTC'ye çevirir."""
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetime yazılamaz; datetime.now(UTC) veya ZoneInfo kullanın.")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        """Veritabanından okunan değere UTC zaman dilimini ekler."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    """Tüm ORM modellerinin taban sınıfı."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def __repr__(self) -> str:
        """Hata ayıklamayı kolaylaştıran kısa gösterim."""
        pk_columns = [column.name for column in self.__table__.primary_key]
        parts: list[str] = []
        for name in pk_columns:
            value: Any = getattr(self, name, None)
            parts.append(f"{name}={value!r}")
        return f"<{type(self).__name__} {' '.join(parts)}>"


class TimestampMixin:
    """`created_at` / `updated_at` sütunlarını ekleyen karışım (mixin)."""

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )
