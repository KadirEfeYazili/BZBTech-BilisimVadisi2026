"""Ham HTML arşivinin bütünlük testleri.

Arşiv, biten kampanyaların tek kalan kanıtıdır. Diskteki dosya ile
`raw_html_sha256` alanı eşleşmezse arşivin kanıt değeri kaybolur.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx

from app.config import Settings
from app.scrapers.fetcher import Fetcher
from app.utils.hashing import sha256_text

# Satır sonları bilinçli olarak CRLF: hatanın ortaya çıktığı koşul budur.
CRLF_HTML = (
    "<html>\r\n<head><title>Kampanya</title></head>\r\n"
    "<body>\r\n<main><p>Kampanya 31.12.2026 tarihine kadar geçerlidir.</p></main>\r\n"
    "</body>\r\n</html>\r\n"
)


def _fetcher(tmp_path: Path, transport: httpx.MockTransport) -> Fetcher:
    settings = Settings(
        raw_html_dir=str(tmp_path / "raw_html"),
        scraper_request_delay_seconds=0.0,
        scraper_max_retries=1,
        database_url="sqlite:///:memory:",
    )
    client = httpx.Client(transport=transport, follow_redirects=True)
    return Fetcher("test_banka", settings=settings, client=client)


class TestArsivButunlugu:
    def test_crlf_iceren_sayfa_ozeti_bozulmadan_saklanir(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        """⚠️ `Path.write_text` Windows'ta her `\\r\\n` değerini `\\r\\r\\n` yapar.

        Bu durumda diskteki dosya `raw_html_sha256` ile artık eşleşmez ve
        arşivin bütünlük güvencesi hiçbir hata üretmeden kaybolur.
        """
        url = "https://ornek.com.tr/kampanya"
        fetcher = _fetcher(tmp_path, make_transport({url: (200, CRLF_HTML)}))

        try:
            sonuc = fetcher.fetch(url)
        finally:
            fetcher.close()

        assert sonuc.raw_html_path is not None
        assert sonuc.raw_html_sha256 is not None

        dosya = tmp_path / "raw_html" / sonuc.raw_html_path
        assert dosya.is_file()

        # Diskteki baytlar, kaydedilen özetle birebir eşleşmeli.
        diskteki = dosya.read_bytes().decode("utf-8")
        assert sha256_text(diskteki) == sonuc.raw_html_sha256
        assert diskteki == sonuc.html

    def test_satir_sonlari_degistirilmez(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        url = "https://ornek.com.tr/kampanya"
        fetcher = _fetcher(tmp_path, make_transport({url: (200, CRLF_HTML)}))

        try:
            sonuc = fetcher.fetch(url)
        finally:
            fetcher.close()

        assert sonuc.raw_html_path is not None
        ham = (tmp_path / "raw_html" / sonuc.raw_html_path).read_bytes()

        assert ham.count(b"\r\n") == CRLF_HTML.count("\r\n")
        assert b"\r\r\n" not in ham

    def test_hata_yaniti_da_arsivlenir(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        """404 gövdesi, biten kampanyalarda tek kalan kanıttır."""
        fetcher = _fetcher(tmp_path, make_transport({}))

        try:
            sonuc = fetcher.fetch("https://ornek.com.tr/biten-kampanya")
        finally:
            fetcher.close()

        assert sonuc.status_code == 404
        assert sonuc.raw_html_path is not None
        assert (tmp_path / "raw_html" / sonuc.raw_html_path).is_file()

    def test_degisen_icerik_eski_anlik_goruntuyu_ezmez(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        """⚠️ Dosya adı yalnızca URL'den türetilirse arşiv üzerine yazılır.

        Sayfalar her istekte birazcık değişiyor (oturum çerezi, güvenlik
        nonce'ı). Üzerine yazma durumunda eski `source_documents` kayıtlarının
        `raw_html_sha256` değeri diskteki dosyayla eşleşmez ve "ham HTML asla
        kaybolmaz" güvencesi sessizce ortadan kalkar.
        """
        url = "https://ornek.com.tr/kampanya"
        ilk_html = CRLF_HTML
        ikinci_html = CRLF_HTML.replace("31.12.2026", "31.01.2027")

        fetcher = _fetcher(tmp_path, make_transport({url: (200, ilk_html)}))
        try:
            ilk = fetcher.fetch(url)
        finally:
            fetcher.close()

        fetcher = _fetcher(tmp_path, make_transport({url: (200, ikinci_html)}))
        try:
            ikinci = fetcher.fetch(url)
        finally:
            fetcher.close()

        assert ilk.raw_html_path != ikinci.raw_html_path

        arsiv = tmp_path / "raw_html"
        ilk_dosya = arsiv / str(ilk.raw_html_path)
        ikinci_dosya = arsiv / str(ikinci.raw_html_path)

        # Her iki anlık görüntü de korunmalı ve kendi özetiyle eşleşmeli.
        assert sha256_text(ilk_dosya.read_bytes().decode("utf-8")) == ilk.raw_html_sha256
        assert sha256_text(ikinci_dosya.read_bytes().decode("utf-8")) == ikinci.raw_html_sha256
        assert "31.12.2026" in ilk_dosya.read_text(encoding="utf-8", newline="")
        assert "31.01.2027" in ikinci_dosya.read_text(encoding="utf-8", newline="")

    def test_ayni_icerik_tek_dosyada_saklanir(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        """İçerik değişmediyse yeni dosya oluşturulmaz."""
        url = "https://ornek.com.tr/kampanya"

        for _ in range(2):
            fetcher = _fetcher(tmp_path, make_transport({url: (200, CRLF_HTML)}))
            try:
                fetcher.fetch(url)
            finally:
                fetcher.close()

        dosyalar = list((tmp_path / "raw_html" / "test_banka").glob("*.html"))
        assert len(dosyalar) == 1

    def test_cekim_gecmisi_tutuluyor(
        self, tmp_path: Path, make_transport: Callable[..., httpx.MockTransport]
    ) -> None:
        """Listeleme sayfaları da `source_documents`'a yazılabilmeli."""
        url = "https://ornek.com.tr/kampanya"
        fetcher = _fetcher(tmp_path, make_transport({url: (200, CRLF_HTML)}))

        try:
            fetcher.fetch(url)
            fetcher.fetch("https://ornek.com.tr/yok")
        finally:
            fetcher.close()

        assert len(fetcher.history) == 2
        assert [item.url for item in fetcher.history] == [url, "https://ornek.com.tr/yok"]
