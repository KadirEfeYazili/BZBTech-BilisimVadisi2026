"""Soft-404 sezgilerinin testleri.

Analizde doğrulanan iki gerçek vakayı temsil eder.
"""

from __future__ import annotations

import pytest

from app.scrapers.soft404 import content_fingerprint, is_soft_404

# Vakıf Katılım: HTTP 200 döner ama başlıkta "404", gövdede hata metni vardır.
VAKIF_SOFT_404 = """
<html><head><title>404 - Sayfa Bulunamadı</title></head>
<body><main><h1>404</h1><p>Aradığınız sayfa yok yada bulunamadı.</p></main></body></html>
"""

# Adil Katılım: geçersiz her adres için ANA SAYFAYI 200 ile döndürür.
# Başlıkta veya gövdede hiçbir hata ifadesi YOKTUR.
ADIL_ANA_SAYFA = """
<html><head><title>Adil Katılım Bankası</title></head>
<body><main>
  <h1>Adil Katılım Bankası</h1>
  <p>Katılım bankacılığı ilkeleriyle yanınızdayız. Şubelerimiz ve dijital
  kanallarımız aracılığıyla hizmet vermekteyiz.</p>
</main></body></html>
"""

GECERLI_KAMPANYA = """
<html><head><title>Akaryakıt Kampanyası</title></head>
<body><main>
  <h1>Akaryakıt Kampanyası</h1>
  <p>Kampanya 1-31 Ağustos 2026 tarihleri arasında geçerlidir ve
  1.500 TL üzeri harcamalarda 200 TL hediye kazandırır.</p>
</main></body></html>
"""


class TestMetinDeseniSezgisi:
    def test_baslikta_404_gecen_sayfa(self) -> None:
        assert is_soft_404(VAKIF_SOFT_404, "https://ornek/kampanya/yok") is True

    @pytest.mark.parametrize(
        "govde",
        [
            "<html><body><p>Aradığınız sayfa bulunamadı.</p></body></html>",
            "<html><body><p>Böyle bir sayfa yok.</p></body></html>",
            "<html><body><p>Page not found</p></body></html>",
        ],
    )
    def test_govde_hata_metinleri(self, govde: str) -> None:
        assert is_soft_404(govde, "https://ornek/x") is True

    def test_gecerli_kampanya_sayfasi_soft_404_degildir(self) -> None:
        assert is_soft_404(GECERLI_KAMPANYA, "https://ornek/kampanya/akaryakit") is False


class TestIcerikOzetiSezgisi:
    """Adil Katılım senaryosu: metin deseni sezgisi tek başına YETMEZ."""

    def test_metin_deseni_ana_sayfayi_yakalayamaz(self) -> None:
        """Ana sayfa hiçbir hata ifadesi içermediği için desen sezgisi başarısızdır."""
        assert is_soft_404(ADIL_ANA_SAYFA, "https://ornek/gecersiz-adres") is False

    def test_icerik_ozeti_ana_sayfayi_yakalar(self) -> None:
        """Bilinen ana sayfa özeti verildiğinde soft-404 tespit edilir."""
        bilinen = {content_fingerprint(ADIL_ANA_SAYFA)}
        assert (
            is_soft_404(
                ADIL_ANA_SAYFA,
                "https://ornek/gecersiz-adres",
                known_soft_404_hashes=bilinen,
            )
            is True
        )

    def test_farkli_icerik_ozet_esleşmez(self) -> None:
        bilinen = {content_fingerprint(ADIL_ANA_SAYFA)}
        assert (
            is_soft_404(
                GECERLI_KAMPANYA,
                "https://ornek/kampanya",
                known_soft_404_hashes=bilinen,
            )
            is False
        )


class TestBosYanitlar:
    @pytest.mark.parametrize("html", [None, "", "   "])
    def test_bos_govde_soft_404_sayilir(self, html: str | None) -> None:
        assert is_soft_404(html, "https://ornek/x") is True


class TestIcerikOzeti:
    def test_ayni_icerik_ayni_ozet(self) -> None:
        assert content_fingerprint(ADIL_ANA_SAYFA) == content_fingerprint(ADIL_ANA_SAYFA)

    def test_farkli_icerik_farkli_ozet(self) -> None:
        assert content_fingerprint(ADIL_ANA_SAYFA) != content_fingerprint(GECERLI_KAMPANYA)

    def test_bos_girdi_bos_ozet(self) -> None:
        assert content_fingerprint(None) == ""
