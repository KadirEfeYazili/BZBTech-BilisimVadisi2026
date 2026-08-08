"""Ortak yanıt şemaları: sayfalama ve hata gövdesi."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Sayfalı liste yanıtı.

    ⚠️ Boş sonuç bir HATA DEĞİLDİR: filtreye uyan kayıt yoksa HTTP 200 ile
    `items: []` döner. Hatalar 4xx/5xx ile `ErrorResponse` gövdesinde bildirilir.
    Bu ayrım arayüzde "veri yok" ile "veri alınamadı" durumlarının
    karıştırılmamasını sağlar.
    """

    items: list[T]
    total: int = Field(description="Filtreye uyan toplam kayıt sayısı")
    page: int = Field(description="Geçerli sayfa (1'den başlar)")
    page_size: int = Field(description="Sayfa başına kayıt sayısı")
    total_pages: int = Field(description="Toplam sayfa sayısı")

    @classmethod
    def create(cls, items: list[T], total: int, page: int, page_size: int) -> Page[T]:
        """Sayfa nesnesini toplam sayfa hesabıyla birlikte üretir."""
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class ErrorDetail(BaseModel):
    """Hata gövdesinin iç kısmı."""

    code: str = Field(description="Makine tarafından okunabilir hata kodu")
    message: str = Field(description="Kullanıcıya gösterilebilir Türkçe mesaj")
    detail: str | None = Field(default=None, description="Ek bağlam")


class ErrorResponse(BaseModel):
    """Tüm hata yanıtlarının tek biçimli gövdesi."""

    error: ErrorDetail


class HealthResponse(BaseModel):
    """Sağlık denetimi yanıtı."""

    status: str
    version: str
    db_ok: bool
    campaign_count: int
