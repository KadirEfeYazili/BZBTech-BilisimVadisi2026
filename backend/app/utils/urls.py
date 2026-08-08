"""URL karşılaştırma yardımcıları.

Bankaların çoğu `www.` ön ekli ve ön eksiz adresler arasında yönlendirme
yapıyor. Analizde doğrulandı: Hayat Finans'ta `www.hayatfinans.com.tr`
adresi `hayatfinans.com.tr` adresine yönleniyor ve sitemap'teki 358 adresin
tamamı ön eksiz yazılmış. Ham dize karşılaştırması bu adresleri "dış bağlantı"
sayar ve keşif sonucu SIFIR olur — üstelik hiçbir hata üretmeden.
"""

from __future__ import annotations

from urllib.parse import urlsplit


def normalize_host(host: str) -> str:
    """Alan adını karşılaştırma için sadeleştirir (küçük harf, `www.` atılır)."""
    return host.lower().removeprefix("www.")


def host_of(url: str) -> str:
    """Adresin sadeleştirilmiş alan adını döndürür."""
    return normalize_host(urlsplit(url).netloc)


def is_same_site(url: str, reference: str) -> bool:
    """İki adres aynı siteye mi ait?

    Göreli adresler (alan adı içermeyenler) aynı site kabul edilir.

    Args:
        url: Denetlenecek adres.
        reference: Sitenin temel adresi.

    Returns:
        Aynı siteye aitse True.
    """
    netloc = urlsplit(url).netloc
    if not netloc:
        return True
    return normalize_host(netloc) == host_of(reference)
