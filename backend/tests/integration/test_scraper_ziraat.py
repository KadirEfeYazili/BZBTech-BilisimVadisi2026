"""Ziraat Katılım scraper testleri.

Testler ağa çıkmaz: kaydedilmiş HTML fixture'ları `httpx.MockTransport`
üzerinden servis edilir (§13).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Campaign, ScrapeRun, SourceDocument
from app.scrapers.banks.ziraat_katilim import BASE_URL, CATEGORIES, ZiraatKatilimScraper
from app.scrapers.fetcher import Fetcher
from app.scrapers.models import DiscoveredUrl

KATEGORI = "kart-kampanyalari"
LISTE_URL = f"{BASE_URL}/kampanyalar/{KATEGORI}"
ARSIV_URL = f"{LISTE_URL}?IsArchived=true"

AKARYAKIT_URL = f"{BASE_URL}/kart-kampanyalari/akaryakitta-250-tl-bonus"
MARKET_URL = f"{BASE_URL}/kart-kampanyalari/markette-taksit-firsati-2"
ETICARET_URL = f"{BASE_URL}/kart-kampanyalari/e-ticarette-indirim"

ROBOTS = "User-agent: *\nAllow: /\n"


@pytest.fixture
def fixtures(read_fixture) -> dict[str, str]:  # type: ignore[no-untyped-def]
    """Ziraat fixture'larını okur."""
    return {
        "liste": read_fixture("html/ziraat_katilim/kampanyalar_kart.html"),
        "son_gun": read_fixture("html/ziraat_katilim/kampanya_son_gun.html"),
        "aralik": read_fixture("html/ziraat_katilim/kampanya_aralik.html"),
    }


def _scraper(
    tmp_path: Path,
    transport: httpx.MockTransport,
    **kwargs: object,
) -> ZiraatKatilimScraper:
    """Sahte taşıyıcıya bağlı, hız sınırı kapalı scraper üretir."""
    settings = Settings(
        raw_html_dir=str(tmp_path / "raw_html"),
        scraper_request_delay_seconds=0.0,
        scraper_max_retries=2,
        airgap_mode=False,
    )
    client = httpx.Client(transport=transport, follow_redirects=True)
    fetcher = Fetcher("ziraat_katilim", settings=settings, client=client)
    return ZiraatKatilimScraper(fetcher=fetcher, settings=settings, **kwargs)  # type: ignore[arg-type]


class TestKesif:
    """`discover()` — 15 kategori sayfası üzerinden."""

    def test_kanonik_detay_kalibi_toplanir(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        transport = make_transport({LISTE_URL: (200, fixtures["liste"])})
        scraper = _scraper(tmp_path, transport, categories=[KATEGORI])
        try:
            bulunan = scraper.discover()
        finally:
            scraper.close()

        adresler = {d.url for d in bulunan}
        assert AKARYAKIT_URL in adresler
        assert MARKET_URL in adresler
        assert ETICARET_URL in adresler

    def test_donem_eki_korunur(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        """⚠️ Slug sonundaki `-2` yeni dönem yayınıdır, kırpılmaz."""
        transport = make_transport({LISTE_URL: (200, fixtures["liste"])})
        scraper = _scraper(tmp_path, transport, categories=[KATEGORI])
        try:
            adresler = {d.url for d in scraper.discover()}
        finally:
            scraper.close()

        assert any(url.endswith("markette-taksit-firsati-2") for url in adresler)

    def test_493_donduren_kalip_izlenmez(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        """⚠️ `/bireysel/kampanyalar/` kalıbı WAF'a takılıyor; keşfe girmemeli."""
        transport = make_transport({LISTE_URL: (200, fixtures["liste"])})
        scraper = _scraper(tmp_path, transport, categories=[KATEGORI])
        try:
            adresler = {d.url for d in scraper.discover()}
        finally:
            scraper.close()

        assert not any("/bireysel/kampanyalar/" in url for url in adresler)

    def test_dis_baglanti_ve_kategori_koku_elenir(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        transport = make_transport({LISTE_URL: (200, fixtures["liste"])})
        scraper = _scraper(tmp_path, transport, categories=[KATEGORI])
        try:
            adresler = {d.url for d in scraper.discover()}
        finally:
            scraper.close()

        assert not any("instagram.com" in url for url in adresler)
        assert LISTE_URL not in adresler

    def test_ayni_kampanya_tekillesir(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        """Fixture'da akaryakıt kampanyasına iki bağlantı var."""
        transport = make_transport({LISTE_URL: (200, fixtures["liste"])})
        scraper = _scraper(tmp_path, transport, categories=[KATEGORI])
        try:
            adresler = [d.url for d in scraper.discover()]
        finally:
            scraper.close()

        assert len(adresler) == len(set(adresler))

    def test_banka_kategorisi_kanit_olarak_tasinir(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        """🎁 Bankanın kendi kategorisi sektör etiketinin %100 güvenilir kaynağı."""
        transport = make_transport({LISTE_URL: (200, fixtures["liste"])})
        scraper = _scraper(tmp_path, transport, categories=[KATEGORI])
        try:
            bulunan = scraper.discover()
        finally:
            scraper.close()

        assert all(d.category_hint == KATEGORI for d in bulunan)

    def test_arsiv_sayfasi_da_taranir(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        """`?IsArchived=true` süresi dolmuş kampanyaları açar."""
        transport = make_transport({LISTE_URL: (200, fixtures["liste"])})
        scraper = _scraper(tmp_path, transport, categories=[KATEGORI])
        try:
            scraper.discover()
            cekilen = {f.url for f in scraper.fetcher.history}
        finally:
            scraper.close()

        assert ARSIV_URL in cekilen

    def test_kategori_verilmezse_hepsi_taranir(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        scraper = _scraper(tmp_path, make_transport({}))
        try:
            scraper.discover()
            cekilen = {f.url for f in scraper.fetcher.history}
        finally:
            scraper.close()

        # Her kategori için güncel + arşiv = 2 istek.
        assert len([u for u in cekilen if "/kampanyalar/" in u]) == len(CATEGORIES) * 2

    def test_bilinmeyen_kategori_hepsine_duser(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        """Yazım hatası sessizce sıfır sonuç üretmemeli."""
        scraper = _scraper(tmp_path, make_transport({}), categories=["olmayan-kategori"])
        try:
            scraper.discover()
            cekilen = {f.url for f in scraper.fetcher.history}
        finally:
            scraper.close()

        assert len([u for u in cekilen if "/kampanyalar/" in u]) == len(CATEGORIES) * 2

    def test_kategori_alinamazsa_digerleri_surer(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        """Bir kategori 404 verse bile keşif devam eder."""
        transport = make_transport({LISTE_URL: (200, fixtures["liste"])})
        scraper = _scraper(tmp_path, transport, categories=[KATEGORI, "akaryakit"])
        try:
            adresler = {d.url for d in scraper.discover()}
        finally:
            scraper.close()

        assert AKARYAKIT_URL in adresler


class TestDetayAyristirma:
    """`parse_detail()` — üç tarih biçimi ve metin alanları."""

    def _hint(self) -> DiscoveredUrl:
        return DiscoveredUrl(
            url=AKARYAKIT_URL,
            doc_type="campaign",
            category_hint=KATEGORI,
            segment_hint="bireysel",
        )

    def test_son_gun_bicimi_yalnizca_bitis_verir(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        """⚠️ "Son Gün 07.09.2026" — başlangıç UYDURULMAZ."""
        scraper = _scraper(tmp_path, make_transport({}))
        try:
            ham = scraper.parse_detail(fixtures["son_gun"], AKARYAKIT_URL, self._hint())
        finally:
            scraper.close()

        assert ham is not None
        assert ham.end_date == date(2026, 9, 7)
        assert ham.start_date is None
        assert ham.date_precision == "partial"

    def test_aralik_biciminde_yil_devralinir(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        """⚠️ "10 Temmuz – 7 Ağustos 2026" — başlangıçta yıl yazılı değil."""
        scraper = _scraper(tmp_path, make_transport({}))
        try:
            ham = scraper.parse_detail(fixtures["aralik"], MARKET_URL, self._hint())
        finally:
            scraper.close()

        assert ham is not None
        assert ham.start_date == date(2026, 7, 10)
        assert ham.end_date == date(2026, 8, 7)

    def test_baslik_h1_den_okunur(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        """`<title>` tüm kampanyalarda aynı; `<h1>` kullanılmalı."""
        scraper = _scraper(tmp_path, make_transport({}))
        try:
            ham = scraper.parse_detail(fixtures["son_gun"], AKARYAKIT_URL, self._hint())
        finally:
            scraper.close()

        assert ham is not None
        assert ham.title == "Akaryakıtta 250 TL Bonus"

    def test_slug_adresten_birebir_okunur(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        """⚠️ Başlıktan türetilmez; Türkçe karakter normalizasyonu tahmin edilemez."""
        scraper = _scraper(tmp_path, make_transport({}))
        try:
            ham = scraper.parse_detail(fixtures["aralik"], MARKET_URL, self._hint())
        finally:
            scraper.close()

        assert ham is not None
        assert ham.external_slug == "markette-taksit-firsati-2"

    def test_kosullar_ve_istisnalar_ayri_alanlarda(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        scraper = _scraper(tmp_path, make_transport({}))
        try:
            ham = scraper.parse_detail(fixtures["son_gun"], AKARYAKIT_URL, self._hint())
        finally:
            scraper.close()

        assert ham is not None
        assert ham.conditions_text and "2.500 TL" in ham.conditions_text
        assert ham.exclusions_text and "Nakit avans" in ham.exclusions_text

    def test_arsiv_bayragi_yalnizca_arsiv_adresinde(
        self,
        tmp_path: Path,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        scraper = _scraper(tmp_path, make_transport({}))
        try:
            guncel = scraper.parse_detail(fixtures["son_gun"], AKARYAKIT_URL, self._hint())
            arsiv = scraper.parse_detail(
                fixtures["son_gun"], f"{AKARYAKIT_URL}?IsArchived=true", self._hint()
            )
        finally:
            scraper.close()

        assert guncel is not None and not guncel.is_archived
        assert arsiv is not None and arsiv.is_archived

    def test_baslik_yoksa_none_doner(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        scraper = _scraper(tmp_path, make_transport({}))
        try:
            ham = scraper.parse_detail("<html><body></body></html>", AKARYAKIT_URL, self._hint())
        finally:
            scraper.close()

        assert ham is None


class TestUctanUcaCalistirma:
    """`run()` — keşif, çekim, arşiv ve kayıt."""

    def _transport(
        self, fixtures: dict[str, str], make_transport: Callable[..., httpx.MockTransport]
    ) -> httpx.MockTransport:
        return make_transport(
            {
                LISTE_URL: (200, fixtures["liste"]),
                AKARYAKIT_URL: (200, fixtures["son_gun"]),
                MARKET_URL: (200, fixtures["aralik"]),
                ETICARET_URL: (200, fixtures["son_gun"]),
            }
        )

    def test_kampanyalar_kaydedilir(
        self,
        tmp_path: Path,
        seeded_session: Session,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        scraper = _scraper(
            tmp_path, self._transport(fixtures, make_transport), categories=[KATEGORI]
        )
        try:
            sonuc = scraper.run(seeded_session)
        finally:
            scraper.close()

        assert sonuc.campaigns_new == 3
        assert seeded_session.scalar(select(Campaign).where(Campaign.title.like("Akaryakıt%")))

    def test_limit_cekimi_daraltir_ama_kesfi_gizlemez(
        self,
        tmp_path: Path,
        seeded_session: Session,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        """Pilot doğrulama: 5 adresle sınırlı çekim."""
        scraper = _scraper(
            tmp_path, self._transport(fixtures, make_transport), categories=[KATEGORI], limit=2
        )
        try:
            sonuc = scraper.run(seeded_session)
        finally:
            scraper.close()

        assert sonuc.urls_discovered == 3
        assert sonuc.campaigns_new == 2

    def test_ikinci_calistirma_kayit_cogaltmaz(
        self,
        tmp_path: Path,
        seeded_session: Session,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        """⚠️ Upsert: aynı komut iki kez çalışınca kayıt sayısı ARTMAZ."""
        for _ in range(2):
            scraper = _scraper(
                tmp_path, self._transport(fixtures, make_transport), categories=[KATEGORI]
            )
            try:
                scraper.run(seeded_session)
            finally:
                scraper.close()

        assert (
            seeded_session.scalar(select(Campaign).where(Campaign.bank_id.isnot(None))) is not None
        )
        toplam = len(list(seeded_session.scalars(select(Campaign))))
        assert toplam == 3

    def test_ham_html_arsivlenir_ve_ozet_tutar(
        self,
        tmp_path: Path,
        seeded_session: Session,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        """Ham HTML diskte olmalı ve `raw_html_sha256` ile eşleşmeli."""
        from app.utils.hashing import sha256_text

        scraper = _scraper(
            tmp_path, self._transport(fixtures, make_transport), categories=[KATEGORI]
        )
        try:
            scraper.run(seeded_session)
        finally:
            scraper.close()

        belgeler = list(
            seeded_session.scalars(
                select(SourceDocument).where(SourceDocument.raw_html_path.isnot(None))
            )
        )
        assert belgeler

        arsiv_kok = tmp_path / "raw_html"
        for belge in belgeler:
            dosya = arsiv_kok / str(belge.raw_html_path)
            assert dosya.is_file()
            assert sha256_text(dosya.read_bytes().decode("utf-8")) == belge.raw_html_sha256

    def test_calistirma_kaydi_dogru_sayilarla_kapanir(
        self,
        tmp_path: Path,
        seeded_session: Session,
        fixtures: dict[str, str],
        make_transport: Callable[..., httpx.MockTransport],
    ) -> None:
        scraper = _scraper(
            tmp_path, self._transport(fixtures, make_transport), categories=[KATEGORI]
        )
        try:
            sonuc = scraper.run(seeded_session)
        finally:
            scraper.close()

        kayit = seeded_session.scalar(select(ScrapeRun).where(ScrapeRun.id == sonuc.run_id))
        assert kayit is not None
        assert kayit.finished_at is not None
        assert kayit.campaigns_new == 3
        assert kayit.status in ("success", "partial")
