"""Scraper kaydı: banka kodu → scraper sınıfı eşlemesi.

Yeni bir banka eklemek için tek yapılacak, sınıfı burada kaydetmektir.
CLI ve testler scraper'lara yalnızca bu kayıt üzerinden erişir.
"""

from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.scrapers.banks.emlak_katilim import EmlakKatilimScraper
from app.scrapers.banks.hayat_finans import HayatFinansScraper
from app.scrapers.base import BaseScraper

# PART 1 kapsamındaki scraper'lar. Kalan 9 banka PART 2'de eklenecek.
BANK_REGISTRY: dict[str, type[BaseScraper]] = {
    EmlakKatilimScraper.bank_code: EmlakKatilimScraper,
    HayatFinansScraper.bank_code: HayatFinansScraper,
}


def available_banks() -> list[str]:
    """Kayıtlı scraper'ların banka kodlarını sıralı döndürür."""
    return sorted(BANK_REGISTRY)


def get_scraper(bank_code: str, **kwargs: object) -> BaseScraper:
    """Banka koduna karşılık gelen scraper örneğini üretir.

    Args:
        bank_code: Banka kodu (ör. "emlak_katilim").
        **kwargs: Scraper yapıcısına aktarılacak argümanlar.

    Returns:
        Scraper örneği.

    Raises:
        NotFoundError: Banka için kayıtlı scraper yoksa.
    """
    scraper_class = BANK_REGISTRY.get(bank_code)
    if scraper_class is None:
        raise NotFoundError(
            f"'{bank_code}' için kayıtlı scraper yok. "
            f"Kullanılabilir: {', '.join(available_banks())}"
        )
    return scraper_class(**kwargs)  # type: ignore[arg-type]
