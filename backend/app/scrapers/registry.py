"""Scraper kaydı: banka kodu → scraper sınıfı eşlemesi.

Yeni bir banka eklemek için tek yapılacak, sınıfı burada kaydetmektir.
CLI ve testler scraper'lara yalnızca bu kayıt üzerinden erişir.
"""

from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.scrapers.banks.adil_katilim import AdilKatilimScraper
from app.scrapers.banks.albaraka import AlbarakaScraper
from app.scrapers.banks.dunya_katilim import DunyaKatilimScraper
from app.scrapers.banks.emlak_katilim import EmlakKatilimScraper
from app.scrapers.banks.hayat_finans import HayatFinansScraper
from app.scrapers.banks.kuveyt_turk import KuveytTurkScraper
from app.scrapers.banks.tom_bank import TomBankScraper
from app.scrapers.banks.turkiye_finans import TurkiyeFinansScraper
from app.scrapers.banks.vakif_katilim import VakifKatilimScraper
from app.scrapers.banks.ziraat_katilim import ZiraatKatilimScraper
from app.scrapers.base import BaseScraper

# Kapsamdaki 10 katılım bankasının tamamı kayıtlıdır.
#
# ⚠️ Adil Katılım kampanya ÜRETMEZ ama listede DURUR: şartname "faaliyet
# gösteren kuruluşların tümü" diyor ve "veri yok" bilgisi de bir bulgudur.
# Çıkarılırsa o bankanın hiç denetlenmediği izlenimi doğar.
BANK_REGISTRY: dict[str, type[BaseScraper]] = {
    AdilKatilimScraper.bank_code: AdilKatilimScraper,
    AlbarakaScraper.bank_code: AlbarakaScraper,
    DunyaKatilimScraper.bank_code: DunyaKatilimScraper,
    EmlakKatilimScraper.bank_code: EmlakKatilimScraper,
    HayatFinansScraper.bank_code: HayatFinansScraper,
    KuveytTurkScraper.bank_code: KuveytTurkScraper,
    TomBankScraper.bank_code: TomBankScraper,
    TurkiyeFinansScraper.bank_code: TurkiyeFinansScraper,
    VakifKatilimScraper.bank_code: VakifKatilimScraper,
    ZiraatKatilimScraper.bank_code: ZiraatKatilimScraper,
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
