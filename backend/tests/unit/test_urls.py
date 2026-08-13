"""URL karşılaştırma ve tekilleştirme testleri.

⚠️ En kritik test `test_camelcase_path_korunur`: gerçek veride doğrulandı,
path küçük harfe çevrilirse adres HTTP 404 döner ve o kampanya kaybolur.
"""

from __future__ import annotations

import pytest

from app.utils.hashing import canonicalize_url
from app.utils.urls import (
    canonical_key,
    dedupe_urls,
    host_of,
    is_same_site,
    normalize_host,
    same_page,
)


class TestAlanAdi:
    """`normalize_host`, `host_of`, `is_same_site`."""

    def test_www_yok_sayilir(self) -> None:
        assert normalize_host("www.hayatfinans.com.tr") == "hayatfinans.com.tr"

    def test_buyuk_harf_kucultulur(self) -> None:
        assert normalize_host("WWW.Ornek.COM.TR") == "ornek.com.tr"

    def test_host_adresten_cikarilir(self) -> None:
        assert host_of("https://www.ornek.com.tr/a/b?c=1") == "ornek.com.tr"

    def test_www_farki_ayni_site_sayilir(self) -> None:
        """Hayat Finans `www.` ön eklisinden ön eksize yönlendiriyor."""
        assert is_same_site("https://hayatfinans.com.tr/k", "https://www.hayatfinans.com.tr")

    def test_goreli_adres_ayni_site_sayilir(self) -> None:
        assert is_same_site("/kampanyalar/akaryakit", "https://ornek.com.tr")

    def test_farkli_alan_adi_dis_baglanti(self) -> None:
        assert not is_same_site("https://baska.com/k", "https://ornek.com.tr")


class TestKanonikAnahtar:
    """`canonical_key` — "aynı sayfa mı" karşılaştırması."""

    def test_camelcase_path_korunur(self) -> None:
        """⚠️ Dünya Katılım `altin-kesemTicari`; küçültülürse 404.

        Türkiye Finans'ta da `tasit-Finansmani.aspx` ve
        `Kar-Payi-Oranlari.aspx` var.
        """
        for yol in ("/altin-kesemTicari", "/tr/tasit-Finansmani.aspx", "/Kar-Payi-Oranlari.aspx"):
            assert yol in canonical_key(f"https://ornek.com.tr{yol}")

    def test_sema_https_e_sabitlenir(self) -> None:
        assert canonical_key("http://ornek.com.tr/k") == "https://ornek.com.tr/k"

    def test_www_atilir(self) -> None:
        assert canonical_key("https://www.ornek.com.tr/k") == "https://ornek.com.tr/k"

    def test_sondaki_slash_atilir(self) -> None:
        assert canonical_key("https://ornek.com.tr/k/") == canonical_key("https://ornek.com.tr/k")

    def test_fragment_atilir(self) -> None:
        assert canonical_key("https://ornek.com.tr/k#detay") == "https://ornek.com.tr/k"

    def test_izleme_parametreleri_atilir(self) -> None:
        """Aynı kampanya farklı kaynaktan gelince iki kez çekilmemeli."""
        kirli = "https://ornek.com.tr/k?utm_source=mail&utm_campaign=agustos&gclid=xyz"
        assert canonical_key(kirli) == "https://ornek.com.tr/k"

    def test_anlamli_sorgu_korunur(self) -> None:
        """⚠️ Ziraat'te `?IsArchived=true` bambaşka içerik döndürür."""
        anahtar = canonical_key("https://ornek.com.tr/kampanyalar?IsArchived=true")
        assert "IsArchived=true" in anahtar

    def test_sorgu_alfabetik_siralanir(self) -> None:
        """Parametre sırası değişen aynı sayfa iki kez çekilmemeli."""
        assert canonical_key("https://ornek.com.tr/k?b=2&a=1") == canonical_key(
            "https://ornek.com.tr/k?a=1&b=2"
        )

    def test_izleme_parametresi_buyuk_harfle_de_atilir(self) -> None:
        assert canonical_key("https://ornek.com.tr/k?UTM_SOURCE=mail") == "https://ornek.com.tr/k"

    @pytest.mark.parametrize(
        ("bir", "iki"),
        [
            ("https://ornek.com.tr/k", "http://www.ornek.com.tr/k/"),
            ("https://ornek.com.tr/k?a=1", "https://ornek.com.tr/k?a=1&fbclid=z"),
            ("https://ornek.com.tr/k#x", "https://ornek.com.tr/k"),
        ],
    )
    def test_ayni_sayfa_taninir(self, bir: str, iki: str) -> None:
        assert same_page(bir, iki)

    def test_farkli_sayfa_ayirt_edilir(self) -> None:
        assert not same_page("https://ornek.com.tr/a", "https://ornek.com.tr/b")
        assert not same_page(
            "https://ornek.com.tr/k", "https://ornek.com.tr/k?IsArchived=true"
        )


class TestTekillestirme:
    """`dedupe_urls`."""

    def test_ayni_sayfalar_tekillesir(self) -> None:
        adresler = [
            "https://ornek.com.tr/k/a",
            "https://www.ornek.com.tr/k/a/",
            "http://ornek.com.tr/k/a?utm_source=x",
            "https://ornek.com.tr/k/b",
        ]
        assert dedupe_urls(adresler) == ["https://ornek.com.tr/k/a", "https://ornek.com.tr/k/b"]

    def test_ilk_gorulen_yazim_korunur(self) -> None:
        """Bankanın listeleme sayfasındaki yazım sitemap'inkine tercih edilir."""
        adresler = ["https://www.ornek.com.tr/k/A", "https://ornek.com.tr/k/A"]
        assert dedupe_urls(adresler) == ["https://www.ornek.com.tr/k/A"]

    def test_bos_liste(self) -> None:
        assert dedupe_urls([]) == []


class TestArsivKimligiAyri:
    """⚠️ `canonicalize_url` arşiv kimliğidir; `canonical_key` ile karıştırılmaz."""

    def test_arsiv_kimligi_www_yi_atmaz(self) -> None:
        """Davranışı değişirse mevcut arşiv dosya adlarıyla eşleşme kopar."""
        assert canonicalize_url("https://www.ornek.com.tr/k") == "https://www.ornek.com.tr/k"

    def test_arsiv_kimligi_semayi_degistirmez(self) -> None:
        assert canonicalize_url("http://ornek.com.tr/k").startswith("http://")

    def test_arsiv_kimligi_sondaki_slashi_korur(self) -> None:
        assert canonicalize_url("https://ornek.com.tr/k/") == "https://ornek.com.tr/k/"

    def test_iki_fonksiyon_farkli_sonuc_verir(self) -> None:
        url = "http://www.ornek.com.tr/k/?utm_source=mail"
        assert canonicalize_url(url) != canonical_key(url)
