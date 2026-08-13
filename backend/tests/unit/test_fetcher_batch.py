"""Toplu çekim, iptal, ilerleme ve WAF yeniden denemesi testleri.

Testler ağa çıkmaz: `httpx.MockTransport` kullanılır (§13).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Event

import httpx
import pytest

from app.config import Settings
from app.scrapers.fetcher import Fetcher

ROBOTS = "User-agent: *\nAllow: /\n"


def _fetcher(tmp_path: Path, transport: httpx.MockTransport) -> Fetcher:
    """Diske geçici arşiv yazan, hız sınırı kapalı bir çekici üretir."""
    settings = Settings(
        raw_html_dir=str(tmp_path / "raw_html"),
        # Testler beklemesin; hız sınırı davranışı ayrıca ölçülür.
        scraper_request_delay_seconds=0.0,
        scraper_max_retries=3,
        airgap_mode=False,
    )
    client = httpx.Client(transport=transport, follow_redirects=True)
    return Fetcher("ornek_banka", settings=settings, client=client)


class TestTopluCekim:
    """`fetch_many`."""

    def test_tum_adresler_sirayla_cekilir(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        adresler = [f"https://ornek.com.tr/k/{i}" for i in range(5)]
        rotalar = {url: (200, f"<html><body>{url}</body></html>") for url in adresler}

        fetcher = _fetcher(tmp_path, make_transport(rotalar))
        try:
            sonuclar = fetcher.fetch_many(adresler)
        finally:
            fetcher.close()

        assert len(sonuclar) == 5
        assert [s.url for s in sonuclar] == adresler
        assert all(s.is_success for s in sonuclar)

    def test_tek_adres_hatasi_digerlerini_durdurmaz(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        """Rotada olmayan adres 404 döner; döngü devam etmeli."""
        adresler = [
            "https://ornek.com.tr/k/1",
            "https://ornek.com.tr/yok",
            "https://ornek.com.tr/k/2",
        ]
        rotalar = {
            "https://ornek.com.tr/k/1": (200, "<html><body>bir</body></html>"),
            "https://ornek.com.tr/k/2": (200, "<html><body>iki</body></html>"),
        }

        fetcher = _fetcher(tmp_path, make_transport(rotalar))
        try:
            sonuclar = fetcher.fetch_many(adresler)
        finally:
            fetcher.close()

        assert len(sonuclar) == 3
        assert sonuclar[1].status_code == 404
        assert sonuclar[2].is_success

    def test_bos_liste_bos_sonuc(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        fetcher = _fetcher(tmp_path, make_transport({}))
        try:
            assert fetcher.fetch_many([]) == []
        finally:
            fetcher.close()


class TestIlerlemeGeriCagrisi:
    """`on_progress` — arayüzdeki ilerleme çubuğunu besler."""

    def test_her_adresten_sonra_cagrilir(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        adresler = [f"https://ornek.com.tr/k/{i}" for i in range(3)]
        rotalar = dict.fromkeys(adresler, (200, "<html><body>x</body></html>"))
        adimlar: list[tuple[int, int]] = []

        fetcher = _fetcher(tmp_path, make_transport(rotalar))
        try:
            fetcher.fetch_many(adresler, on_progress=lambda d, t: adimlar.append((d, t)))
        finally:
            fetcher.close()

        assert adimlar == [(1, 3), (2, 3), (3, 3)]


class TestIptal:
    """`cancel_event` — kullanıcı tetiklemeli çekimin durdurulabilmesi."""

    def test_onceden_kurulmus_olay_hic_cekim_yapmaz(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        olay = Event()
        olay.set()

        fetcher = _fetcher(tmp_path, make_transport({}))
        try:
            sonuclar = fetcher.fetch_many(
                ["https://ornek.com.tr/k/1", "https://ornek.com.tr/k/2"], cancel_event=olay
            )
        finally:
            fetcher.close()

        assert sonuclar == []

    def test_ortada_iptal_edilince_tamamlananlar_doner(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        """İptal veri kaybettirmez: o ana kadar çekilenler elde kalır."""
        adresler = [f"https://ornek.com.tr/k/{i}" for i in range(5)]
        rotalar = dict.fromkeys(adresler, (200, "<html><body>x</body></html>"))
        olay = Event()

        def _ikiden_sonra_iptal(tamamlanan: int, _toplam: int) -> None:
            if tamamlanan == 2:
                olay.set()

        fetcher = _fetcher(tmp_path, make_transport(rotalar))
        try:
            sonuclar = fetcher.fetch_many(
                adresler, cancel_event=olay, on_progress=_ikiden_sonra_iptal
            )
        finally:
            fetcher.close()

        assert len(sonuclar) == 2
        assert all(s.is_success for s in sonuclar)


class TestWafYenidenDeneme:
    """⚠️ HTTP 493 — Ziraat Katılım'ın WAF'ı bu standart dışı kodu döndürüyor."""

    def test_493_kalici_hata_sayilmaz_ve_yeniden_denenir(self, tmp_path: Path) -> None:
        cagri_sayisi = {"adet": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url).endswith("/robots.txt"):
                return httpx.Response(200, text=ROBOTS)
            cagri_sayisi["adet"] += 1
            # İlk iki denemede WAF'a takıl, üçüncüde geç.
            if cagri_sayisi["adet"] < 3:
                return httpx.Response(493, text="WAF")
            return httpx.Response(
                200,
                text="<html><body>Kampanya</body></html>",
                headers={"content-type": "text/html; charset=utf-8"},
            )

        fetcher = _fetcher(tmp_path, httpx.MockTransport(handler))
        try:
            sonuc = fetcher.fetch("https://ziraatkatilim.com.tr/kampanyalar/kart")
        finally:
            fetcher.close()

        assert cagri_sayisi["adet"] == 3
        assert sonuc.is_success

    def test_surekli_493_kalici_hataya_doner(self, tmp_path: Path) -> None:
        """Deneme hakkı bitince çalıştırma durmaz, hata kaydedilir."""

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url).endswith("/robots.txt"):
                return httpx.Response(200, text=ROBOTS)
            return httpx.Response(493, text="WAF")

        fetcher = _fetcher(tmp_path, httpx.MockTransport(handler))
        try:
            sonuc = fetcher.fetch("https://ziraatkatilim.com.tr/kampanyalar")
        finally:
            fetcher.close()

        assert sonuc.status_code == 493
        assert not sonuc.is_success
        assert sonuc.error is not None

    @pytest.mark.parametrize("durum", [408, 425, 429, 500, 503])
    def test_diger_gecici_durumlar_da_yeniden_denenir(self, tmp_path: Path, durum: int) -> None:
        cagri_sayisi = {"adet": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url).endswith("/robots.txt"):
                return httpx.Response(200, text=ROBOTS)
            cagri_sayisi["adet"] += 1
            if cagri_sayisi["adet"] == 1:
                return httpx.Response(durum, text="gecici")
            return httpx.Response(
                200,
                text="<html><body>ok</body></html>",
                headers={"content-type": "text/html; charset=utf-8"},
            )

        fetcher = _fetcher(tmp_path, httpx.MockTransport(handler))
        try:
            sonuc = fetcher.fetch("https://ornek.com.tr/k")
        finally:
            fetcher.close()

        assert cagri_sayisi["adet"] == 2
        assert sonuc.is_success

    def test_404_yeniden_denenmez(self, tmp_path: Path) -> None:
        """Kalıcı hata boşuna tekrarlanmaz; bankaya gereksiz yük binmez."""
        cagri_sayisi = {"adet": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url).endswith("/robots.txt"):
                return httpx.Response(200, text=ROBOTS)
            cagri_sayisi["adet"] += 1
            return httpx.Response(404, text="<html><title>404</title></html>")

        fetcher = _fetcher(tmp_path, httpx.MockTransport(handler))
        try:
            fetcher.fetch("https://ornek.com.tr/silinmis")
        finally:
            fetcher.close()

        assert cagri_sayisi["adet"] == 1


class TestHamBaytErisimi:
    """⚠️ Gzip'li sitemap için ham bayt gerekiyor."""

    def test_content_alani_ham_baytlari_tasir(self, tmp_path: Path) -> None:
        """`html` (metin) okunursa gzip baytları bozulur ve sitemap boş döner."""
        import gzip

        xml = b'<?xml version="1.0"?><urlset><url><loc>https://x/a</loc></url></urlset>'
        sikistirilmis = gzip.compress(xml)

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url).endswith("/robots.txt"):
                return httpx.Response(200, text=ROBOTS)
            return httpx.Response(200, content=sikistirilmis, headers={"content-type": "text/xml"})

        fetcher = _fetcher(tmp_path, httpx.MockTransport(handler))
        try:
            sonuc = fetcher.fetch("https://ornek.com.tr/sitemap.xml")
        finally:
            fetcher.close()

        assert sonuc.content == sikistirilmis
        assert gzip.decompress(sonuc.content or b"") == xml
