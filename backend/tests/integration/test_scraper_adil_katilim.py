"""Adil Katılım scraper testleri.

Testler ağa çıkmaz (§13).

Bu bankanın testi "kampanya bulundu mu" değil, "ÇÖP KAYIT ÜRETİLMEDİ Mİ"
sorusunu ölçer. Site var olmayan her adres için ana sayfayı HTTP 200 ile
döndürüyor; içerik özeti karşılaştırması yapılmazsa dokuz aday adresin
dokuzu da geçerli kampanya sanılır.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Campaign, ScrapeRun, SourceDocument
from app.scrapers.banks.adil_katilim import BASE_URL, CANDIDATE_PATHS, AdilKatilimScraper
from app.scrapers.fetcher import Fetcher
from app.scrapers.models import DiscoveredUrl


@pytest.fixture
def anasayfa(read_fixture) -> str:  # type: ignore[no-untyped-def]
    return read_fixture("html/adil_katilim/anasayfa.html")


def _catch_all_transport(anasayfa_html: str) -> httpx.MockTransport:
    """⚠️ Gerçek davranışın kopyası: HER adres ana sayfayı döndürür."""

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/robots.txt"):
            return httpx.Response(200, text="")
        return httpx.Response(
            200, text=anasayfa_html, headers={"content-type": "text/html; charset=utf-8"}
        )

    return httpx.MockTransport(handler)


def _scraper(tmp_path: Path, transport: httpx.MockTransport) -> AdilKatilimScraper:
    settings = Settings(
        raw_html_dir=str(tmp_path / "raw_html"),
        scraper_request_delay_seconds=0.0,
        scraper_max_retries=2,
        airgap_mode=False,
    )
    client = httpx.Client(transport=transport, follow_redirects=True)
    fetcher = Fetcher("adil_katilim", settings=settings, client=client)
    return AdilKatilimScraper(fetcher=fetcher, settings=settings)


class TestSoftNotFoundCatchAll:
    """⚠️ Metin desenine bakan sezgi bu bankada çalışmaz."""

    def test_ana_sayfa_parmak_izi_kaydedilir(self, tmp_path: Path, anasayfa: str) -> None:
        scraper = _scraper(tmp_path, _catch_all_transport(anasayfa))
        try:
            scraper.discover()
            # Ana sayfa keşfin İLK isteği olmalı: özet öğrenilmeden yapılan
            # hiçbir denetim işe yaramaz.
            assert scraper.fetcher.history[0].url == f"{BASE_URL}/"
        finally:
            scraper.close()

    def test_tum_adaylar_soft_404_isaretlenir(self, tmp_path: Path, anasayfa: str) -> None:
        scraper = _scraper(tmp_path, _catch_all_transport(anasayfa))
        try:
            adaylar = scraper.discover()
            sonuclar = [scraper.fetcher.fetch(d.url) for d in adaylar]
        finally:
            scraper.close()

        assert len(sonuclar) == len(CANDIDATE_PATHS)
        assert all(s.status_code == 200 for s in sonuclar)
        assert all(s.is_soft_404 for s in sonuclar)
        assert not any(s.is_success for s in sonuclar)

    def test_ana_sayfa_alinamazsa_kesif_durur(self, tmp_path: Path) -> None:
        """Parmak izi yoksa denetim yapılamaz; çöp kayıt riskine girilmez."""

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url).endswith("/robots.txt"):
                return httpx.Response(200, text="")
            return httpx.Response(500, text="")

        scraper = _scraper(tmp_path, httpx.MockTransport(handler))
        try:
            assert scraper.discover() == []
        finally:
            scraper.close()


class TestKampanyaUretilmez:
    """`parse_detail()` daima None döner."""

    def test_parse_detail_none_doner(self, tmp_path: Path, anasayfa: str) -> None:
        scraper = _scraper(tmp_path, _catch_all_transport(anasayfa))
        try:
            hint = DiscoveredUrl(url=f"{BASE_URL}/kampanyalar", doc_type="campaign")
            assert scraper.parse_detail(anasayfa, f"{BASE_URL}/kampanyalar", hint) is None
        finally:
            scraper.close()


class TestUctanUca:
    """`run()` — sıfır kampanya, ama çalıştırma kaydı ve kanıt var."""

    def test_hicbir_kampanya_kaydedilmez(
        self, tmp_path: Path, seeded_session: Session, anasayfa: str
    ) -> None:
        """⚠️ Denetim çalışmazsa burada 9 çöp kayıt oluşurdu."""
        scraper = _scraper(tmp_path, _catch_all_transport(anasayfa))
        try:
            sonuc = scraper.run(seeded_session)
        finally:
            scraper.close()

        assert sonuc.campaigns_new == 0
        assert sonuc.campaigns_updated == 0
        assert list(seeded_session.scalars(select(Campaign))) == []

    def test_calistirma_kaydi_yine_de_olusur(
        self, tmp_path: Path, seeded_session: Session, anasayfa: str
    ) -> None:
        """ "Veri yok" bilgisi de bir bulgudur; gizlenmez."""
        scraper = _scraper(tmp_path, _catch_all_transport(anasayfa))
        try:
            sonuc = scraper.run(seeded_session)
        finally:
            scraper.close()

        kayit = seeded_session.scalar(select(ScrapeRun).where(ScrapeRun.id == sonuc.run_id))
        assert kayit is not None
        assert kayit.finished_at is not None
        assert kayit.campaigns_new == 0
        assert kayit.urls_discovered == len(CANDIDATE_PATHS)

    def test_bakildigi_belgelenir(
        self, tmp_path: Path, seeded_session: Session, anasayfa: str
    ) -> None:
        """Her aday adres `source_documents`'a yazılır: "bakıldı ve yoktu" kanıtı."""
        scraper = _scraper(tmp_path, _catch_all_transport(anasayfa))
        try:
            scraper.run(seeded_session)
        finally:
            scraper.close()

        belgeler = list(seeded_session.scalars(select(SourceDocument)))
        assert len(belgeler) >= len(CANDIDATE_PATHS)
        assert all(b.is_soft_404 for b in belgeler if b.url != f"{BASE_URL}/")

    def test_ham_html_arsivlenir(
        self, tmp_path: Path, seeded_session: Session, anasayfa: str
    ) -> None:
        scraper = _scraper(tmp_path, _catch_all_transport(anasayfa))
        try:
            scraper.run(seeded_session)
        finally:
            scraper.close()

        assert list((tmp_path / "raw_html" / "adil_katilim").glob("*.html"))
