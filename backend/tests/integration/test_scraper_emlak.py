"""Emlak Katılım scraper'ının uçtan uca testi — kayıtlı HTML fixture'ları ile.

Gerçek ağa ÇIKILMAZ: `httpx.MockTransport` kayıtlı sayfaları döndürür.
Bu test hem ayrıştırmayı hem de `BaseScraper.run()` şablon metodunun tamamını
(çekim → arşiv → source_documents → upsert → scrape_runs) doğrular.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Campaign, ScrapeRun, SourceDocument
from app.scrapers.banks.emlak_katilim import BASE_URL, EmlakKatilimScraper
from app.scrapers.fetcher import Fetcher

BIREYSEL_LISTING = f"{BASE_URL}/tr/bireysel/kampanyalar"
KURUMSAL_LISTING = f"{BASE_URL}/tr/kurumsal/kampanyalar"
AKARYAKIT_URL = f"{BASE_URL}/tr/bireysel/kampanyalar/kampanya/akaryakit-harcamalarina-200-tl-hediye"
MARKET_URL = (
    f"{BASE_URL}/tr/bireysel/kampanyalar/kampanya/market-alisverislerinde-kazandiran-firsat"
)
# Bu adres bilinçli olarak eşlemeye KONMADI: 404 döner ve tek bir URL hatasının
# tüm çalıştırmayı durdurmadığı doğrulanır.
KONUT_URL = f"{BASE_URL}/tr/bireysel/kampanyalar/kampanya/konut-finansmaninda-masrafsiz-donem"


@pytest.fixture
def scraper_ortami(
    tmp_path: Path,
    read_fixture: Callable[[str], str],
    make_transport: Callable[..., httpx.MockTransport],
) -> tuple[EmlakKatilimScraper, Settings]:
    """Sahte taşıyıcıya bağlı, geçici arşiv dizini kullanan scraper üretir."""
    listing = read_fixture("html/emlak_katilim/kampanyalar_bireysel.html")
    akaryakit = read_fixture("html/emlak_katilim/kampanya_akaryakit.html")
    market = read_fixture("html/emlak_katilim/kampanya_market.html")

    transport = make_transport(
        {
            BIREYSEL_LISTING: (200, listing),
            KURUMSAL_LISTING: (200, "<html><body><main><h1>Kurumsal</h1></main></body></html>"),
            AKARYAKIT_URL: (200, akaryakit),
            MARKET_URL: (200, market),
        }
    )

    settings = Settings(
        raw_html_dir=str(tmp_path / "raw_html"),
        scraper_request_delay_seconds=0.0,
        scraper_max_retries=1,
        database_url="sqlite:///:memory:",
    )
    client = httpx.Client(transport=transport, follow_redirects=True)
    fetcher = Fetcher("emlak_katilim", settings=settings, client=client)
    return EmlakKatilimScraper(fetcher=fetcher, settings=settings), settings


class TestKesif:
    def test_uc_kampanya_kesfedilir(
        self, scraper_ortami: tuple[EmlakKatilimScraper, Settings]
    ) -> None:
        scraper, _ = scraper_ortami
        discovered = scraper.discover()
        urls = {item.url for item in discovered}

        assert AKARYAKIT_URL in urls
        assert MARKET_URL in urls
        assert KONUT_URL in urls

    def test_listeleme_ve_dis_baglantilar_elenir(
        self, scraper_ortami: tuple[EmlakKatilimScraper, Settings]
    ) -> None:
        scraper, _ = scraper_ortami
        urls = {item.url for item in scraper.discover()}

        assert BIREYSEL_LISTING not in urls
        assert not any("instagram" in url for url in urls)

    def test_segment_listeleme_adresinden_gelir(
        self, scraper_ortami: tuple[EmlakKatilimScraper, Settings]
    ) -> None:
        """Detay sayfasında segment etiketi yok; bilgi keşiften taşınır."""
        scraper, _ = scraper_ortami
        akaryakit = next(i for i in scraper.discover() if i.url == AKARYAKIT_URL)
        assert akaryakit.segment_hint == "bireysel"
        assert akaryakit.doc_type == "campaign"


class TestCalistirma:
    def test_calistirma_ozeti(
        self,
        scraper_ortami: tuple[EmlakKatilimScraper, Settings],
        seeded_session: Session,
    ) -> None:
        scraper, _ = scraper_ortami
        result = scraper.run(seeded_session)

        assert result.urls_discovered == 3
        assert result.urls_fetched == 3
        assert result.campaigns_new == 2
        # Eksik sayfa çalıştırmayı durdurmaz, yalnızca kısmi başarı üretir.
        assert result.errors_count == 1
        assert result.status == "partial"

    def test_scrape_runs_kaydi_kapatilir(
        self,
        scraper_ortami: tuple[EmlakKatilimScraper, Settings],
        seeded_session: Session,
    ) -> None:
        scraper, _ = scraper_ortami
        scraper.run(seeded_session)

        run_row = seeded_session.scalar(select(ScrapeRun))
        assert run_row is not None
        assert run_row.status == "partial"
        assert run_row.finished_at is not None
        assert run_row.campaigns_new == 2
        assert run_row.error_log is not None

    def test_basarisiz_cekim_de_kaydedilir(
        self,
        scraper_ortami: tuple[EmlakKatilimScraper, Settings],
        seeded_session: Session,
    ) -> None:
        """404 yanıtı da belgelenir: verinin neden eksik olduğu kanıtlanabilmeli."""
        scraper, _ = scraper_ortami
        scraper.run(seeded_session)

        konut_doc = seeded_session.scalar(
            select(SourceDocument).where(SourceDocument.url == KONUT_URL)
        )
        assert konut_doc is not None
        assert konut_doc.http_status == 404

    def test_listeleme_sayfalari_da_kaydedilir(
        self,
        scraper_ortami: tuple[EmlakKatilimScraper, Settings],
        seeded_session: Session,
    ) -> None:
        scraper, _ = scraper_ortami
        scraper.run(seeded_session)

        listing_doc = seeded_session.scalar(
            select(SourceDocument).where(SourceDocument.url == BIREYSEL_LISTING)
        )
        assert listing_doc is not None
        assert listing_doc.doc_type == "listing"

    def test_ham_html_arsivlenir(
        self,
        scraper_ortami: tuple[EmlakKatilimScraper, Settings],
        seeded_session: Session,
    ) -> None:
        """Emlak Katılım'da arşiv yok; ham HTML saklanmazsa veri geri gelmez."""
        scraper, settings = scraper_ortami
        scraper.run(seeded_session)

        arsiv_dizini = settings.raw_html_path / "emlak_katilim"
        assert arsiv_dizini.exists()
        assert len(list(arsiv_dizini.glob("*.html"))) >= 3

        doc = seeded_session.scalar(
            select(SourceDocument).where(SourceDocument.url == AKARYAKIT_URL)
        )
        assert doc is not None
        assert doc.raw_html_path is not None
        assert doc.raw_html_sha256 is not None
        assert (settings.raw_html_path / doc.raw_html_path).exists()

    def test_ikinci_calistirma_kayit_cogaltmaz(
        self,
        scraper_ortami: tuple[EmlakKatilimScraper, Settings],
        seeded_session: Session,
    ) -> None:
        """Upsert anahtarı (bank_id + external_slug) tekrarları engeller."""
        scraper, _ = scraper_ortami
        scraper.run(seeded_session)
        ikinci = scraper.run(seeded_session)

        assert ikinci.campaigns_new == 0
        assert ikinci.campaigns_updated == 2

        toplam = seeded_session.scalar(select(func.count()).select_from(Campaign))
        assert toplam == 2


class TestAyristirma:
    @pytest.fixture
    def kampanyalar(
        self,
        scraper_ortami: tuple[EmlakKatilimScraper, Settings],
        seeded_session: Session,
    ) -> dict[str, Campaign]:
        scraper, _ = scraper_ortami
        scraper.run(seeded_session)
        return {c.external_slug: c for c in seeded_session.scalars(select(Campaign)).all()}

    def test_slug_url_den_alinir(self, kampanyalar: dict[str, Campaign]) -> None:
        """Slug BAŞLIKTAN ÜRETİLMEZ; href değeri birebir kullanılır."""
        assert "akaryakit-harcamalarina-200-tl-hediye" in kampanyalar

    def test_baslik_ve_segment(self, kampanyalar: dict[str, Campaign]) -> None:
        kampanya = kampanyalar["akaryakit-harcamalarina-200-tl-hediye"]
        assert kampanya.title == "Akaryakıt Harcamalarına 200 TL Hediye"
        assert kampanya.segment == "bireysel"

    def test_tarih_kosul_metninden_cikarilir(self, kampanyalar: dict[str, Campaign]) -> None:
        """ "1-31 Ağustos 2026" biçimi (format 4)."""
        kampanya = kampanyalar["akaryakit-harcamalarina-200-tl-hediye"]
        assert kampanya.start_date == date(2026, 8, 1)
        assert kampanya.end_date == date(2026, 8, 31)
        assert kampanya.date_precision == "exact"

    def test_ilgisiz_tarih_bitis_sanilmaz(self, kampanyalar: dict[str, Campaign]) -> None:
        """Metindeki "15 Ekim 2026" kampanya bitişi DEĞİLDİR."""
        kampanya = kampanyalar["akaryakit-harcamalarina-200-tl-hediye"]
        assert kampanya.end_date != date(2026, 10, 15)

    def test_sms_katilimi(self, kampanyalar: dict[str, Campaign]) -> None:
        kampanya = kampanyalar["akaryakit-harcamalarina-200-tl-hediye"]
        assert kampanya.participation_method == "sms"
        assert kampanya.sms_keyword == "AKARYAKIT"
        assert kampanya.sms_number == "6026"

    def test_kategori_bos_birakilir(self, kampanyalar: dict[str, Campaign]) -> None:
        """Sitede kategori etiketi yok; PART 3'te sınıflandırılacak."""
        kampanya = kampanyalar["akaryakit-harcamalarina-200-tl-hediye"]
        assert kampanya.category is None

    def test_kosullar_ve_istisnalar_ayri_saklanir(self, kampanyalar: dict[str, Campaign]) -> None:
        kampanya = kampanyalar["akaryakit-harcamalarina-200-tl-hediye"]
        assert kampanya.conditions_text is not None
        assert "6026" in kampanya.conditions_text
        assert kampanya.exclusions_text is not None
        assert "Ticari kartlar" in kampanya.exclusions_text

    def test_baslangicsiz_tarih_partial_olur(self, kampanyalar: dict[str, Campaign]) -> None:
        """ "31.12.2026 tarihine kadar" — başlangıç yok."""
        kampanya = kampanyalar["market-alisverislerinde-kazandiran-firsat"]
        assert kampanya.start_date is None
        assert kampanya.end_date == date(2026, 12, 31)
        assert kampanya.date_precision == "partial"

    def test_kupon_kodu(self, kampanyalar: dict[str, Campaign]) -> None:
        kampanya = kampanyalar["market-alisverislerinde-kazandiran-firsat"]
        assert kampanya.coupon_code == "emlak20"
        assert kampanya.participation_method == "kod"

    def test_durum_backendde_hesaplanir(self, kampanyalar: dict[str, Campaign]) -> None:
        """Durum alanı doldurulmuş olmalı; frontend bu hesabı yapmaz."""
        for kampanya in kampanyalar.values():
            assert kampanya.status in ("active", "upcoming", "expired", "unknown")


class TestDryRun:
    def test_dry_run_veritabanina_yazmaz(
        self,
        scraper_ortami: tuple[EmlakKatilimScraper, Settings],
        seeded_session: Session,
    ) -> None:
        scraper, _ = scraper_ortami
        result = scraper.run(seeded_session, dry_run=True)

        assert result.campaigns_new == 2
        assert seeded_session.scalar(select(func.count()).select_from(Campaign)) == 0
        assert seeded_session.scalar(select(func.count()).select_from(ScrapeRun)) == 0
