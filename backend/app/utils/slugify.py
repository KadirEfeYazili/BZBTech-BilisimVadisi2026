"""Slug üretimi — YALNIZCA İÇ KULLANIM İÇİN.

⚠️ UYARI — BU FONKSİYONLA BANKA URL'İ ÜRETİLMEZ.

Analizde doğrulandı: banka kampanya başlıklarında Türkçe karakter ve kesme
işareti bulunuyor, her bankanın slug üretme kuralı farklı ve tahmin edilemiyor.
Başlıktan üretilen URL 404 döndürür. Scraper'lar slug'ı DAİMA sayfadaki
`<a href>` değerinden birebir okur (bkz. `app.scrapers.banks.*`).

Bu modül yalnızca dosya adı, önbellek anahtarı gibi iç kullanımlar içindir.
"""

from __future__ import annotations

import re
from typing import Final

from app.core.normalization.text import ascii_fold_tr, lower_tr, normalize_text

_NON_ALNUM_RE: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9]+")
_MULTI_DASH_RE: Final[re.Pattern[str]] = re.compile(r"-{2,}")


def slugify(value: str | None, *, max_length: int = 80) -> str:
    """Metni ASCII slug biçimine çevirir.

    Türkçe karakterler ASCII karşılıklarına katlanır (ı→i, ş→s, ğ→g ...).

    Args:
        value: Slug'a çevrilecek metin.
        max_length: Sonucun en fazla uzunluğu.

    Returns:
        Küçük harfli, tire ayırıcılı slug; girdi boşsa boş dize.
    """
    if not value:
        return ""

    text = lower_tr(normalize_text(value))
    text = ascii_fold_tr(text)
    text = _NON_ALNUM_RE.sub("-", text)
    text = _MULTI_DASH_RE.sub("-", text).strip("-")

    if len(text) > max_length:
        text = text[:max_length].rstrip("-")

    return text


def slug_from_url_path(url: str) -> str:
    """URL yolunun son anlamlı parçasını döndürür.

    Scraper'ların `external_slug` üretmek için kullandığı yol budur: değer
    URL'den ALINIR, başlıktan üretilmez.

    Args:
        url: Kampanya adresi.

    Returns:
        Yolun son parçası; bulunamazsa boş dize.
    """
    from urllib.parse import urlsplit

    path = urlsplit(url).path.rstrip("/")
    if not path:
        return ""
    return path.rsplit("/", 1)[-1]
