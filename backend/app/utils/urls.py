"""URL karşılaştırma ve tekilleştirme yardımcıları.

Bankaların çoğu `www.` ön ekli ve ön eksiz adresler arasında yönlendirme
yapıyor. Analizde doğrulandı: Hayat Finans'ta `www.hayatfinans.com.tr`
adresi `hayatfinans.com.tr` adresine yönleniyor ve sitemap'teki 358 adresin
tamamı ön eksiz yazılmış. Ham dize karşılaştırması bu adresleri "dış bağlantı"
sayar ve keşif sonucu SIFIR olur — üstelik hiçbir hata üretmeden.

⚠️ `canonical_key()` ile `app/utils/hashing.py::canonicalize_url()` KARIŞTIRILMAZ:

  - `canonicalize_url()` ARŞİV KİMLİĞİDİR. `url_hash` ve ham HTML dosya adı
    ondan türer. Davranışı değişirse aynı sayfa yeni bir dosya adına yazılır,
    mevcut arşiv dosyalarıyla eşleşme kopar ve "ham HTML asla kaybolmaz"
    güvencesi sessizce delinir. BU YÜZDEN DEĞİŞTİRİLMEZ.
  - `canonical_key()` KEŞİF ANAHTARIDIR. Yalnızca "bu iki adres aynı sayfa mı"
    sorusunu yanıtlar; hiçbir yerde saklanmaz, istediğimiz gibi sıkılaştırılır.
"""

from __future__ import annotations

from typing import Final
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Sayfanın içeriğini DEĞİŞTİRMEYEN, yalnızca kaynak takibi yapan parametreler.
# Tekilleştirmede yok sayılırlar; aksi hâlde aynı kampanya, farklı kaynaktan
# gelen bağlantılar yüzünden birden çok kez çekilir.
TRACKING_PARAMS: Final[frozenset[str]] = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "gclid",
        "fbclid",
        "msclkid",
        "yclid",
        "mc_cid",
        "mc_eid",
        "_ga",
    }
)


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


def canonical_key(url: str) -> str:
    """Adresi "aynı sayfa mı" karşılaştırması için tek biçime indirger.

    Uygulanan sadeleştirmeler:
      - Şema `https`'e sabitlenir (aynı sayfa iki protokolden gelebiliyor)
      - Alan adı küçük harfe çevrilir, `www.` atılır
      - Sondaki `/` kaldırılır
      - Fragment (`#...`) atılır
      - İzleme parametreleri atılır, kalan sorgu alfabetik sıralanır

    ⚠️ PATH ASLA KÜÇÜK HARFE ÇEVRİLMEZ. Gerçek veride doğrulandı:
    Dünya Katılım'da `altin-kesemTicari`, Türkiye Finans'ta
    `tasit-Finansmani.aspx` ve `Kar-Payi-Oranlari.aspx` gibi camelCase
    slug'lar var; küçük harfe çevrilirse adres HTTP 404 döner.

    ⚠️ Sorgu dizesi ATILMAZ, yalnızca sıralanır: Ziraat Katılım'da
    `?IsArchived=true` bambaşka bir içerik (kampanya arşivi) döndürür.

    Args:
        url: Sadeleştirilecek adres.

    Returns:
        Karşılaştırma için kullanılacak kanonik anahtar.
    """
    parts = urlsplit(url.strip())

    host = normalize_host(parts.netloc)
    # Sondaki `/` anlam taşımaz; kök adreste ("https://x/") tek başına kalır.
    path = parts.path.rstrip("/")

    kalan = [
        (ad, deger)
        for ad, deger in parse_qsl(parts.query, keep_blank_values=True)
        if ad.lower() not in TRACKING_PARAMS
    ]
    query = urlencode(sorted(kalan))

    return urlunsplit(("https", host, path, query, ""))


def same_page(url: str, other: str) -> bool:
    """İki adresin aynı sayfayı gösterip göstermediğini söyler.

    Args:
        url: Birinci adres.
        other: İkinci adres.

    Returns:
        Kanonik anahtarları eşitse True.
    """
    return canonical_key(url) == canonical_key(other)


def dedupe_urls(urls: list[str]) -> list[str]:
    """Aynı sayfayı gösteren adresleri tekilleştirir, sırayı korur.

    İlk görülen yazım korunur: bankanın kendi listeleme sayfasında yazdığı
    biçim, sitemap'ten gelen biçime tercih edilir.

    Args:
        urls: Ham adres listesi.

    Returns:
        Tekilleştirilmiş adresler, ilk görülme sırasıyla.
    """
    gorulen: set[str] = set()
    sonuc: list[str] = []
    for url in urls:
        anahtar = canonical_key(url)
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        sonuc.append(url)
    return sonuc
