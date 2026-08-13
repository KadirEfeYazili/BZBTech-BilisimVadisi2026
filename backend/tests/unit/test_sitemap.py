"""Sitemap ayrıştırma testleri.

Buradaki senaryoların hepsi gerçek banka sitelerinde ölçüldü. Ortak özellikleri
**hata fırlatmadan boş sonuç üretmeleri**: gzip'i açmayan ya da sitemap index'i
tanımayan bir ayrıştırıcı sıfır adres döndürür ve keşif sessizce çöker.
"""

from __future__ import annotations

import gzip

from app.scrapers.sitemap import (
    decode_sitemap,
    extract_urls,
    is_gzipped,
    is_sitemap_index,
    parse_sitemap,
    sitemap_urls_from_robots,
)

URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://ornek.com.tr/kampanyalar/akaryakit</loc>
    <lastmod>2026-08-01</lastmod>
  </url>
  <url>
    <loc>https://ornek.com.tr/kampanyalar/market</loc>
  </url>
  <url>
    <loc>https://ornek.com.tr/hakkimizda</loc>
  </url>
</urlset>
"""

SITEMAPINDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://ornek.com.tr/sitemap-kampanyalar.xml</loc>
    <lastmod>2026-08-01</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://ornek.com.tr/sitemap-urunler.xml</loc>
  </sitemap>
</sitemapindex>
"""

# Ad alanı bildirmeyen sitemap — bazı bankalar böyle yayımlıyor.
URLSET_NAMESPACESIZ = """<?xml version="1.0"?>
<urlset>
  <url><loc>https://ornek.com.tr/kampanyalar/tatil</loc></url>
</urlset>
"""


class TestGzipTespiti:
    """⚠️ Gzip, `.xml` uzantısıyla servis ediliyor."""

    def test_gzip_magic_byte_ile_taninir(self) -> None:
        assert is_gzipped(gzip.compress(URLSET.encode("utf-8")))

    def test_duz_xml_gzip_sayilmaz(self) -> None:
        assert not is_gzipped(URLSET.encode("utf-8"))

    def test_bos_govde_gzip_sayilmaz(self) -> None:
        assert not is_gzipped(b"")

    def test_gzipli_sitemap_acilir(self) -> None:
        """Hayat Finans, T.O.M. Bank ve Dünya Katılım'da doğrulandı."""
        sikistirilmis = gzip.compress(URLSET.encode("utf-8"))
        assert len(parse_sitemap(sikistirilmis)) == 3

    def test_bozuk_gzip_bos_doner(self) -> None:
        """Bozuk arşiv keşfi durdurmaz; çağıran başka yönteme geçer."""
        assert decode_sitemap(b"\x1f\x8b" + b"bozuk veri") == ""
        assert parse_sitemap(b"\x1f\x8b" + b"bozuk veri") == []


class TestSitemapAyristirma:
    """`<urlset>` ve `<sitemapindex>`."""

    def test_urlset_okunur(self) -> None:
        kayitlar = parse_sitemap(URLSET)
        assert [k.loc for k in kayitlar] == [
            "https://ornek.com.tr/kampanyalar/akaryakit",
            "https://ornek.com.tr/kampanyalar/market",
            "https://ornek.com.tr/hakkimizda",
        ]

    def test_lastmod_okunur(self) -> None:
        assert parse_sitemap(URLSET)[0].lastmod == "2026-08-01"
        assert parse_sitemap(URLSET)[1].lastmod is None

    def test_sitemap_index_taninir(self) -> None:
        """⚠️ `<urlset>` bekleyen ayrıştırıcı burada sessizce boş döner."""
        assert is_sitemap_index(SITEMAPINDEX)
        assert not is_sitemap_index(URLSET)

    def test_sitemap_index_alt_adresleri_verir(self) -> None:
        kayitlar = parse_sitemap(SITEMAPINDEX)
        assert [k.loc for k in kayitlar] == [
            "https://ornek.com.tr/sitemap-kampanyalar.xml",
            "https://ornek.com.tr/sitemap-urunler.xml",
        ]

    def test_namespacesiz_sitemap_okunur(self) -> None:
        """Etiket adı ad alanından arındırılarak karşılaştırılır."""
        assert len(parse_sitemap(URLSET_NAMESPACESIZ)) == 1


class TestBozukGirdi:
    """Kırık sitemap tüm keşfi durdurmaz."""

    def test_bozuk_xml_bos_doner(self) -> None:
        assert parse_sitemap("<urlset><url><loc>yarim") == []

    def test_bos_govde_bos_doner(self) -> None:
        assert parse_sitemap(b"") == []
        assert parse_sitemap("   ") == []

    def test_html_govdesi_bos_doner(self) -> None:
        """Türkiye Finans'ın sitemap'i giriş sayfasına yönleniyor."""
        assert parse_sitemap("<html><body>Giriş yapınız</body></html>") == []

    def test_loc_etiketi_olmayan_kayit_atlanir(self) -> None:
        xml = "<urlset><url><lastmod>2026-08-01</lastmod></url></urlset>"
        assert parse_sitemap(xml) == []

    def test_utf8_disi_bayt_keşfi_durdurmaz(self) -> None:
        bozuk = URLSET.encode("utf-8").replace(b"akaryakit", b"akary\xffkit")
        assert len(parse_sitemap(bozuk)) == 3


class TestAdresSuzme:
    """`extract_urls` — site ve yol süzgeçleri."""

    def test_yol_suzgeci(self) -> None:
        adresler = extract_urls(URLSET, path_contains="kampanya")
        assert len(adresler) == 2
        assert all("kampanya" in url for url in adresler)

    def test_ayni_site_suzgeci_www_yok_sayar(self) -> None:
        """Hayat Finans `www.` ön ekli adresten ön eksize yönlendiriyor."""
        adresler = extract_urls(URLSET, same_site_as="https://www.ornek.com.tr")
        assert len(adresler) == 3

    def test_dis_baglanti_elenir(self) -> None:
        xml = (
            "<urlset>"
            "<url><loc>https://ornek.com.tr/kampanyalar/a</loc></url>"
            "<url><loc>https://baska-site.com/kampanyalar/b</loc></url>"
            "</urlset>"
        )
        adresler = extract_urls(xml, same_site_as="https://ornek.com.tr")
        assert adresler == ["https://ornek.com.tr/kampanyalar/a"]

    def test_adres_degistirilmeden_doner(self) -> None:
        """⚠️ camelCase slug korunur; küçük harfe çevrilirse 404 alınır."""
        xml = "<urlset><url><loc>https://ornek.com.tr/altin-kesemTicari</loc></url></urlset>"
        assert extract_urls(xml, path_contains="ticari") == [
            "https://ornek.com.tr/altin-kesemTicari"
        ]

    def test_tekrar_eden_adresler_tekillesir(self) -> None:
        xml = (
            "<urlset>"
            "<url><loc>https://ornek.com.tr/kampanya/a</loc></url>"
            "<url><loc>https://www.ornek.com.tr/kampanya/a/</loc></url>"
            "</urlset>"
        )
        assert len(extract_urls(xml)) == 1


class TestRobotsSitemapSatiri:
    """`sitemap_urls_from_robots`."""

    def test_sitemap_satirlari_okunur(self) -> None:
        robots = (
            "User-agent: *\n"
            "Disallow: /gizli\n"
            "Sitemap: https://ornek.com.tr/sitemap.xml\n"
            "sitemap: https://ornek.com.tr/sitemap-2.xml\n"
        )
        assert sitemap_urls_from_robots(robots) == [
            "https://ornek.com.tr/sitemap.xml",
            "https://ornek.com.tr/sitemap-2.xml",
        ]

    def test_sitemap_satiri_yoksa_bos(self) -> None:
        assert sitemap_urls_from_robots("User-agent: *\nAllow: /\n") == []

    def test_baska_alan_adi_da_dondurulur(self) -> None:
        """⚠️ Dünya Katılım'ın robots.txt'i yanlış alan adı gösteriyor.

        Süzme çağıranın işidir; bu fonksiyon bildirileni olduğu gibi verir.
        """
        robots = "Sitemap: https://blueprint.com.tr/sitemap.xml\n"
        assert sitemap_urls_from_robots(robots) == ["https://blueprint.com.tr/sitemap.xml"]
