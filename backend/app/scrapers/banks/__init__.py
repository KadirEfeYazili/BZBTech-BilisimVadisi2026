"""Bankaya özgü scraper uygulamaları.

PART 1'de iki banka uygulanmıştır. Kalan 9 banka PART 2'de eklenecektir;
her biri yalnızca `discover()` ve `parse_detail()` yazarak `BaseScraper`
altyapısını yeniden kullanır.
"""

from app.scrapers.banks.emlak_katilim import EmlakKatilimScraper
from app.scrapers.banks.hayat_finans import HayatFinansScraper

__all__ = ["EmlakKatilimScraper", "HayatFinansScraper"]
