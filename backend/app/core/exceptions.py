"""Uygulama istisnaları.

Tüm özel istisnalar `AppError`dan türer; API katmanı tek bir işleyici ile
tutarlı JSON hata gövdesi üretir (§9).
"""

from __future__ import annotations


class AppError(Exception):
    """Uygulama kaynaklı hataların taban sınıfı.

    Attributes:
        code: Makine tarafından okunabilir hata kodu (ör. NOT_FOUND).
        message: Kullanıcıya gösterilecek Türkçe mesaj.
        status_code: Karşılık gelen HTTP durum kodu.
        detail: Ek bağlam (geliştirme ortamında yanıta eklenir).
    """

    code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class NotFoundError(AppError):
    """İstenen kayıt bulunamadı."""

    code = "NOT_FOUND"
    status_code = 404


class ValidationError(AppError):
    """Girdi doğrulama hatası."""

    code = "VALIDATION_ERROR"
    status_code = 422


class ScraperError(AppError):
    """Kazıma sırasında oluşan genel hata."""

    code = "SCRAPER_ERROR"
    status_code = 500


class AirgapError(ScraperError):
    """AIRGAP_MODE açıkken dış ağa çıkma girişimi.

    On-premise kurulumda sistemin dışarı hiç çıkmadığını garanti eder (§5).
    """

    code = "AIRGAP_MODE_ACTIVE"


class RobotsDisallowedError(ScraperError):
    """robots.txt bu URL'e erişimi yasaklıyor.

    İstek yapılmaz; kayıt `robots_allowed=False` ile belgelenir.
    """

    code = "ROBOTS_DISALLOWED"


class SoftNotFoundError(ScraperError):
    """Yanıt HTTP 200 döndürdü ancak içerik aslında 'sayfa yok'."""

    code = "SOFT_404"
