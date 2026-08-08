"""Kazıma katmanı: keşif, çekim, arşivleme ve ayrıştırma."""

from app.scrapers.base import BaseScraper
from app.scrapers.fetcher import Fetcher
from app.scrapers.models import DiscoveredUrl, FetchResult, RawCampaign, ScrapeRunResult
from app.scrapers.registry import BANK_REGISTRY, available_banks, get_scraper

__all__ = [
    "BANK_REGISTRY",
    "BaseScraper",
    "DiscoveredUrl",
    "FetchResult",
    "Fetcher",
    "RawCampaign",
    "ScrapeRunResult",
    "available_banks",
    "get_scraper",
]
