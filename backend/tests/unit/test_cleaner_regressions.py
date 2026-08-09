"""Gerçek banka sayfalarında tespit edilen hatalar için regresyon testleri.

Bu testlerin tamamı, kurgusal fixture'ların YAKALAYAMADIĞI ve yalnızca gerçek
sayfalar çekildiğinde ortaya çıkan hatalara karşılık gelir. Hepsinin ortak
özelliği, hata fırlatmadan SESSİZCE yanlış veri üretmeleridir.
"""

from __future__ import annotations

from app.core.normalization.date_tr import parse_date_range_tr
from app.processing.cleaner import clean_html, extract_title
from app.utils.urls import host_of, is_same_site, normalize_host


class TestYapisalEtiketIcindekiIcerik:
    """Bozuk HTML, içeriği <nav>/<header> içine düşürebilir."""

    def test_buyuk_nav_icerigi_silinmez(self) -> None:
        """Gerçek vaka: Emlak Katılım kampanya metni <nav> içine düşüyor.

        Koşulsuz <nav> silme, 6308 karakterlik gövdeyi 771'e düşürüyordu.
        """
        icerik = "Kampanya, 31.12.2026 tarihine kadar geçerlidir. " * 40
        html = f"<body><nav><div>{icerik}</div></nav></body>"

        sonuc = clean_html(html)

        assert "31.12.2026" in sonuc
        assert len(sonuc) > 1000

    def test_kucuk_nav_hala_siliniyor(self) -> None:
        """Gerçek gezinme menüsü elenmeye devam etmeli."""
        html = (
            "<body>"
            "<nav><a href='/'>Ana Sayfa</a><a href='/x'>Bireysel</a></nav>"
            "<main><p>" + ("Kampanya koşulları burada yer alır. " * 20) + "</p></main>"
            "</body>"
        )

        sonuc = clean_html(html)

        assert "Ana Sayfa" not in sonuc
        assert "Kampanya koşulları" in sonuc

    def test_form_icindeki_icerik_silinmez(self) -> None:
        """ASP.NET WebForms sayfanın tamamını tek <form> içine sarar."""
        html = (
            "<body><form runat='server'>"
            "<article><p>Kampanya 1-31 Ağustos 2026 tarihleri arasında geçerlidir.</p></article>"
            "</form></body>"
        )

        assert "1-31 Ağustos 2026" in clean_html(html)


class TestAnaIcerikSecimi:
    def test_bos_main_yerine_govde_kullanilir(self) -> None:
        """Gerçek vaka: <main> yalnızca mobil uygulama afişini içeriyor."""
        html = (
            "<body>"
            "<main><p>Mobil uygulamayı indir</p></main>"
            "<article><p>" + ("Kampanya detayları ve koşulları. " * 30) + "</p></article>"
            "</body>"
        )

        sonuc = clean_html(html)

        assert "Kampanya detayları" in sonuc
        assert len(sonuc) > 500

    def test_dolu_main_hala_tercih_edilir(self) -> None:
        html = (
            "<body>"
            "<div class='sidebar'>Yan içerik</div>"
            "<main><p>" + ("Asıl kampanya metni. " * 30) + "</p></main>"
            "</body>"
        )

        sonuc = clean_html(html)

        assert "Asıl kampanya metni" in sonuc
        assert "Yan içerik" not in sonuc


class TestBaslikCikarimi:
    def test_h1_javascript_sablonuysa_h2_kullanilir(self) -> None:
        """Gerçek vaka: <h1> içeriği JS ile üretiliyor, <title> her sayfada aynı."""
        html = (
            "<html><head><title>Kampanya | Türkiye Emlak Katılım Bankası</title></head>"
            '<body><h1>" + pageTitle + "</h1>'
            "<h2>Biletinial'da %20 indirim!</h2></body></html>"
        )

        assert extract_title(html) == "Biletinial'da %20 indirim!"

    def test_bolum_basligi_kampanya_adi_sayilmaz(self) -> None:
        html = (
            "<html><head><title>Yedek Başlık</title></head>"
            "<body><h2>Kampanya Koşulları</h2></body></html>"
        )

        assert extract_title(html) == "Yedek Başlık"

    def test_og_title_yedek_olarak_kullanilir(self) -> None:
        html = (
            "<html><head><meta property='og:title' content='Akaryakıt Kampanyası'>"
            "<title>Genel Başlık</title></head><body><p>metin</p></body></html>"
        )

        assert extract_title(html) == "Akaryakıt Kampanyası"

    def test_gercek_h1_hala_onceliklidir(self) -> None:
        html = "<body><h1>Asıl Başlık</h1><h2>Alt Başlık</h2></body>"
        assert extract_title(html) == "Asıl Başlık"


class TestUctanUcaCikarim:
    def test_gercek_sayfa_yapisindan_tarih_cikarilir(self) -> None:
        """Başlık ve tarih, gerçek sayfa yapısını taklit eden HTML'den çıkarılmalı."""
        html = (
            "<html><head><title>Kampanya | Türkiye Emlak Katılım Bankası</title></head>"
            "<body><form><nav><section><article>"
            "<h2>Uçak Bileti Harcamalarınıza 2.000 TL ParafPara</h2>"
            "<div class='searchContent'><ul>"
            "<li>Kampanya 1-31 Ağustos 2026 tarihleri arasında geçerlidir.</li>"
            "<li>1.500 TL ve üzeri harcamaya 200 TL hediye verilir.</li>"
            "</ul></div>"
            "</article></section></nav></form></body></html>"
        )

        baslik = extract_title(html)
        metin = clean_html(html)
        baslangic, bitis, kesinlik = parse_date_range_tr(metin)

        assert baslik == "Uçak Bileti Harcamalarınıza 2.000 TL ParafPara"
        assert "1.500 TL" in metin
        assert kesinlik == "exact"
        assert baslangic is not None and bitis is not None


class TestAlanAdiKarsilastirmasi:
    """`www.` ön eki yüzünden tüm keşif sonucu sıfıra düşüyordu."""

    def test_www_onekli_ve_oneksiz_ayni_site(self) -> None:
        assert is_same_site(
            "https://hayatfinans.com.tr/kampanyalar/x", "https://www.hayatfinans.com.tr"
        )
        assert is_same_site(
            "https://www.hayatfinans.com.tr/kampanyalar/x", "https://hayatfinans.com.tr"
        )

    def test_farkli_site_reddedilir(self) -> None:
        assert not is_same_site("https://instagram.com/x", "https://www.hayatfinans.com.tr")

    def test_goreli_adres_ayni_site_sayilir(self) -> None:
        assert is_same_site("/kampanyalar/x", "https://www.hayatfinans.com.tr")

    def test_host_sadeleştirme(self) -> None:
        assert normalize_host("WWW.Example.COM") == "example.com"
        assert host_of("https://www.emlakkatilim.com.tr/tr/x") == "emlakkatilim.com.tr"
