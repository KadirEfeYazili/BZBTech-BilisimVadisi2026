"""Soft-404 tespiti — HTTP 200 döndüren "sayfa yok" yanıtlarını yakalar.

Analizde doğrulanan iki gerçek vaka:

  1. Vakıf Katılım — geçersiz slug'da HTTP 200 döndürüyor, `<title>` içinde
     "404" geçiyor ve gövdede "Aradığınız sayfa yok yada bulunamadı" yazıyor.

  2. Adil Katılım — HER geçersiz URL için ana sayfanın HTML'ini HTTP 200 ile
     döndürüyor. Başlıkta veya gövdede hiçbir hata ifadesi YOKTUR; tek ayırt
     edici işaret, içeriğin ana sayfayla birebir aynı olmasıdır.

Bu yüzden iki bağımsız sezgi birlikte uygulanır: metin deseni ve içerik özeti.
"""

from __future__ import annotations

import re
from typing import Final

from app.core.normalization.text import lower_tr
from app.processing.cleaner import clean_html, extract_title
from app.utils.hashing import sha256_text

# Başlıkta bu desenler varsa sayfa yok kabul edilir.
SOFT_404_TITLE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern) for pattern in (r"\b404\b", r"sayfa bulunamadı", r"page not found")
)

# Gövde metninde bu desenler varsa sayfa yok kabul edilir.
SOFT_404_BODY_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern)
    for pattern in (
        r"aradığınız sayfa.{0,30}(bulunamadı|yok)",
        r"sayfa bulunamadı",
        r"böyle bir sayfa (yok|bulunmuyor)",
        r"aradığınız içeriğe ulaşılamadı",
        r"page not found",
        r"error 404",
    )
)

# Gövde deseni araması bu uzunlukla sınırlanır: uzun kampanya metinlerinde
# rastgele geçen "bulunamadı" ifadesi yanlış pozitif üretmesin.
_BODY_SCAN_LIMIT: Final[int] = 2000


def content_fingerprint(html: str | None) -> str:
    """Sayfanın temizlenmiş içeriğinin özetini döndürür.

    Karşılaştırma temiz metin üzerinden yapılır; tarih damgası veya oturum
    kimliği gibi değişken parçalar HTML'de olsa bile temiz metinde bulunmaz.

    Args:
        html: Ham HTML.

    Returns:
        Temiz metnin SHA-256 özeti; içerik yoksa boş dize.
    """
    text = clean_html(html)
    if not text:
        return ""
    return sha256_text(text)


def is_soft_404(
    html: str | None,
    url: str,
    *,
    known_soft_404_hashes: frozenset[str] | set[str] | None = None,
) -> bool:
    """Yanıtın gerçekte "sayfa yok" olup olmadığını belirler.

    Args:
        html: Yanıtın ham HTML gövdesi.
        url: İstenen adres (yalnızca loglama ve gelecekteki sezgiler için).
        known_soft_404_hashes: Bilinen "yer tutucu sayfa" içerik özetleri.
            Adil Katılım gibi her geçersiz URL'de ana sayfayı döndüren siteler
            için scraper bu kümeye ana sayfa özetini koyar.

    Returns:
        Sayfa aslında yoksa True.
    """
    if not html or not html.strip():
        return True

    title = lower_tr(extract_title(html) or "")
    if any(pattern.search(title) for pattern in SOFT_404_TITLE_PATTERNS):
        return True

    body = lower_tr(clean_html(html))[:_BODY_SCAN_LIMIT]
    if any(pattern.search(body) for pattern in SOFT_404_BODY_PATTERNS):
        return True

    if known_soft_404_hashes:
        fingerprint = content_fingerprint(html)
        if fingerprint and fingerprint in known_soft_404_hashes:
            return True

    return False
