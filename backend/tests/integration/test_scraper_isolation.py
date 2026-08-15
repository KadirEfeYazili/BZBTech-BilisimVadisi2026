"""Scraper izolasyonu ve kapsam testleri.

Bir bankanın çökmesi diğerlerini durdurmamalıdır. Demo sırasında sistemi
ayakta tutan şey budur: on siteden biri bugün erişilemez olduğunda çalıştırma
o bankayı `failed` işaretleyip devam eder.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session

from app.config import Settings
from app.scrapers.base import BaseScraper
from app.scrapers.fetcher import Fetcher
from app.scrapers.models import DiscoveredUrl, RawCampaign
from app.scrapers.registry import BANK_REGISTRY, available_banks, get_scraper

# Kapsamdaki 10 katılım bankası. İktisat Katılım ticari faaliyete geçmediği
# için kapsam dışıdır.
BEKLENEN_BANKALAR = {
    "adil_katilim",
    "albaraka",
    "dunya_katilim",
    "emlak_katilim",
    "hayat_finans",
    "kuveyt_turk",
    "tom_bank",
    "turkiye_finans",
    "vakif_katilim",
    "ziraat_katilim",
}


class TestKayit:
    """`registry` — kapsamın tamamı kayıtlı mı?"""

    def test_on_bankanin_tamami_kayitli(self) -> None:
        assert set(available_banks()) == BEKLENEN_BANKALAR

    def test_adil_katilim_listeden_cikarilmamis(self) -> None:
        """Kampanya üretmiyor ama listede DURUR: "veri yok" da bir bulgudur."""
        assert "adil_katilim" in available_banks()

    def test_her_scraper_banka_kodu_tasiyor(self) -> None:
        for kod, sinif in BANK_REGISTRY.items():
            assert sinif.bank_code == kod

    def test_scraperlar_kategori_ve_limit_kabul_eder(self) -> None:
        """Pilot doğrulama tüm bankalarda aynı arayüzle yapılabilmeli."""
        for kod in available_banks():
            scraper = get_scraper(kod, categories=["deneme"], limit=3)
            try:
                assert scraper.limit == 3
                assert scraper.categories == ("deneme",)
            finally:
                scraper.close()


class _CokenScraper(BaseScraper):
    """Keşifte kasıtlı olarak hata fırlatan scraper."""

    bank_code = "emlak_katilim"
    version = "test"

    def discover(self) -> list[DiscoveredUrl]:
        raise RuntimeError("kasıtlı çökme")

    def parse_detail(self, html: str, url: str, hint: DiscoveredUrl) -> RawCampaign | None:
        return None


class _AyristirmadaCokenScraper(BaseScraper):
    """Detay ayrıştırmada hata fırlatan scraper."""

    bank_code = "emlak_katilim"
    version = "test"

    def discover(self) -> list[DiscoveredUrl]:
        return [
            DiscoveredUrl(url=f"https://ornek.com.tr/k/{i}", doc_type="campaign") for i in range(3)
        ]

    def parse_detail(self, html: str, url: str, hint: DiscoveredUrl) -> RawCampaign | None:
        raise RuntimeError(f"kasıtlı çökme: {url}")


def _fetcher(tmp_path: Path) -> Fetcher:
    settings = Settings(
        raw_html_dir=str(tmp_path / "raw_html"),
        scraper_request_delay_seconds=0.0,
        airgap_mode=False,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(
            200,
            text="<html><body><h1>Kampanya</h1></body></html>",
            headers={"content-type": "text/html; charset=utf-8"},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return Fetcher("emlak_katilim", settings=settings, client=client)


class TestHataIzolasyonu:
    """Tek bir hata çalıştırmayı durdurmaz."""

    def test_kesif_cokerse_calistirma_failed_ile_kapanir(
        self, tmp_path: Path, seeded_session: Session
    ) -> None:
        """İstisna DIŞARI SIZMAZ; çağıran döngü diğer bankalara geçebilir."""
        scraper = _CokenScraper(fetcher=_fetcher(tmp_path))
        try:
            sonuc = scraper.run(seeded_session)
        finally:
            scraper.close()

        assert sonuc.status == "failed"
        assert sonuc.errors_count == 1
        assert "kasıtlı çökme" in sonuc.errors[0]

    def test_ayristirma_cokerse_digerleri_denenir(
        self, tmp_path: Path, seeded_session: Session
    ) -> None:
        """Üç adresin üçü de denenir; hata sayılır, döngü kırılmaz."""
        scraper = _AyristirmadaCokenScraper(fetcher=_fetcher(tmp_path))
        try:
            sonuc = scraper.run(seeded_session)
        finally:
            scraper.close()

        assert sonuc.urls_discovered == 3
        assert sonuc.urls_fetched == 3
        assert sonuc.errors_count == 3
        assert sonuc.status == "partial"

    def test_coken_scraper_digerlerini_etkilemez(
        self, tmp_path: Path, seeded_session: Session
    ) -> None:
        """Kasıtlı hatadan sonra başka bir scraper sorunsuz çalışmalı."""
        coken = _CokenScraper(fetcher=_fetcher(tmp_path))
        try:
            coken.run(seeded_session)
        finally:
            coken.close()

        saglam = _AyristirmadaCokenScraper(fetcher=_fetcher(tmp_path))
        try:
            sonuc = saglam.run(seeded_session)
        finally:
            saglam.close()

        assert sonuc.urls_discovered == 3


class TestPlaywrightsizCalisma:
    """⚠️ Playwright OPSİYONEL; kurulu değilken hiçbir şey çökmemeli."""

    def test_tarayici_modulu_ice_aktarilabilir(self) -> None:
        from app.scrapers import browser

        assert isinstance(browser.is_playwright_available(), bool)

    def test_kullanilamazken_acik_hata_mesaji_verir(self) -> None:
        from app.scrapers.browser import browser_page, is_playwright_available

        if is_playwright_available():
            pytest.skip("Playwright kurulu; bu senaryo yalnızca kurulu değilken geçerli")

        with pytest.raises(RuntimeError, match="kur --playwright"), browser_page():
            pass

    def test_hicbir_scraper_playwright_gerektirmez(self) -> None:
        """Kayıtlı scraper'ların tamamı httpx ile çalışır.

        Vakıf ve Dünya Katılım'da liste tarayıcı gerektirebiliyordu; ölçüm
        sonrası ikisi de sunucu HTML'i veya sitemap üzerinden çözüldü.
        """
        import importlib

        for kod in available_banks():
            modul = importlib.import_module(f"app.scrapers.banks.{kod}")
            kaynak = Path(str(modul.__file__)).read_text(encoding="utf-8")
            assert "browser_page" not in kaynak, f"{kod} tarayıcıya bağımlı"
