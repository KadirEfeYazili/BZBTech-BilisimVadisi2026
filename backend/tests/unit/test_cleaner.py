"""HTML temizleyici testleri."""

from __future__ import annotations

import pytest

from app.processing.cleaner import (
    clean_html,
    extract_main_text,
    extract_tables,
    extract_title,
    render_table_text,
)

SAYFA = """
<html>
  <head>
    <title>Emlak Katılım - Akaryakıt Kampanyası</title>
    <script>var x = 'script icerigi';</script>
    <style>.a { color: red }</style>
  </head>
  <body>
    <header><a href="/">Ana Sayfa</a></header>
    <nav><ul><li>Bireysel</li><li>Kurumsal</li></ul></nav>
    <div class="cookie-banner">Çerez Politikası kapsamında tanımlama bilgisi kullanıyoruz.</div>
    <main>
      <h1>Akaryakıt Kampanyası</h1>
      <p>Kampanya <b>1-31 Ağustos 2026</b> tarihleri arasında geçerlidir.</p>
      <h2>Kampanya Koşulları</h2>
      <ul>
        <li>1.500 TL ve üzeri harcamaya 200 TL hediye.</li>
        <li>AKARYAKIT yazıp 6026'ya gönderin.</li>
      </ul>
    </main>
    <footer>Tüm hakları saklıdır. Müşteri Hizmetleri: 0850 222 0 666</footer>
  </body>
</html>
"""


class TestGurultuTemizligi:
    def test_script_ve_style_icerigi_kaldirilir(self) -> None:
        sonuc = clean_html(SAYFA)
        assert "script icerigi" not in sonuc
        assert "color: red" not in sonuc

    def test_nav_header_footer_kaldirilir(self) -> None:
        sonuc = clean_html(SAYFA)
        assert "Ana Sayfa" not in sonuc
        assert "saklıdır" not in sonuc

    def test_cerez_kapsayicisi_kaldirilir(self) -> None:
        assert "tanımlama bilgisi" not in clean_html(SAYFA)


class TestIcerikKorunumu:
    def test_kampanya_metni_korunur(self) -> None:
        sonuc = clean_html(SAYFA)
        assert "Akaryakıt Kampanyası" in sonuc
        assert "1.500 TL ve üzeri harcamaya 200 TL hediye." in sonuc
        assert "6026" in sonuc

    def test_satir_ici_etiket_cumleyi_bolmez(self) -> None:
        """<b> içindeki tarih, cümleden kopmamalı — tarih ayrıştırması buna bağlı."""
        assert "1-31 Ağustos 2026 tarihleri arasında" in clean_html(SAYFA)

    def test_liste_ogeleri_ayri_satirlarda(self) -> None:
        sonuc = clean_html(SAYFA)
        satirlar = [s for s in sonuc.split("\n") if s.strip()]
        assert any(s.startswith("1.500 TL") for s in satirlar)
        assert any(s.startswith("AKARYAKIT") for s in satirlar)


class TestBaslik:
    def test_h1_onceliklidir(self) -> None:
        assert extract_title(SAYFA) == "Akaryakıt Kampanyası"

    def test_h1_yoksa_title_kullanilir(self) -> None:
        html = "<html><head><title>Yedek Başlık</title></head><body><p>x</p></body></html>"
        assert extract_title(html) == "Yedek Başlık"

    @pytest.mark.parametrize("html", [None, "", "<html><body></body></html>"])
    def test_baslik_yoksa_none(self, html: str | None) -> None:
        assert extract_title(html) is None


class TestTablolar:
    TABLO_HTML = """
    <table>
      <tr><th>Vade</th><th>Kâr Payı Oranı</th></tr>
      <tr><td>12 Ay</td><td>%2,05</td></tr>
      <tr><td>24 Ay</td><td>%2,45</td></tr>
    </table>
    """

    def test_tablo_matrisi(self) -> None:
        tablolar = extract_tables(self.TABLO_HTML)
        assert tablolar == [[["Vade", "Kâr Payı Oranı"], ["12 Ay", "%2,05"], ["24 Ay", "%2,45"]]]

    def test_tablo_metne_cevrilirken_yapi_korunur(self) -> None:
        sonuc = clean_html(self.TABLO_HTML)
        assert "Vade | Kâr Payı Oranı" in sonuc
        assert "12 Ay | %2,05" in sonuc

    def test_render_table_text(self) -> None:
        assert render_table_text([["a", "b"], ["c", "d"]]) == "a | b\nc | d"

    @pytest.mark.parametrize("html", [None, "", "<p>tablo yok</p>"])
    def test_tablo_yoksa_bos_liste(self, html: str | None) -> None:
        assert extract_tables(html) == []


class TestGorunmezKarakter:
    def test_tablo_basligindaki_gorunmez_karakterler_temizlenir(self) -> None:
        """Türkiye Finans senaryosu: başlıklarda zero-width space ve nbsp var."""
        zwsp = chr(0x200B)
        nbsp = chr(0x00A0)
        html = f"<table><tr><th>{zwsp}Vade</th><th>Kâr{nbsp}Payı{zwsp} Oranı</th></tr></table>"
        assert extract_tables(html) == [[["Vade", "Kâr Payı Oranı"]]]


class TestBosGirdiler:
    @pytest.mark.parametrize("html", [None, "", "   "])
    def test_bos_girdi_bos_dize(self, html: str | None) -> None:
        assert clean_html(html) == ""
        assert extract_main_text(html) == ""


class TestAnaIcerikSecimi:
    def test_main_etiketi_tercih_edilir(self) -> None:
        html = """
        <body>
          <div class="sidebar">Yan içerik metni</div>
          <main><p>Asıl kampanya metni</p></main>
        </body>
        """
        sonuc = clean_html(html)
        assert "Asıl kampanya metni" in sonuc
        assert "Yan içerik" not in sonuc

    def test_main_yoksa_govde_kullanilir(self) -> None:
        html = "<body><div><p>Gövdedeki metin</p></div></body>"
        assert "Gövdedeki metin" in clean_html(html)

    def test_boilerplate_kapatilabilir(self) -> None:
        html = "<body><main><p>İçerik</p><p>Tüm hakları saklıdır.</p></main></body>"
        assert "saklıdır" in clean_html(html, remove_boilerplate=False)
        assert "saklıdır" not in clean_html(html, remove_boilerplate=True)
