"""Özet (hash) yardımcıları.

İki ayrı amaçla kullanılır:
  1. Ham HTML dosya adı ve bütünlük kontrolü (`raw_html_sha256`)
  2. İçerik bazlı deduplikasyon ve soft-404 tespiti (`clean_text_sha256`)

Adil Katılım her geçersiz URL için ana sayfayı HTTP 200 ile döndürdüğünden,
içerik özeti karşılaştırması soft-404 tespitinin tek güvenilir yoludur.
"""

from __future__ import annotations

import hashlib
from urllib.parse import urlsplit, urlunsplit


def sha256_bytes(data: bytes) -> str:
    """Bayt dizisinin SHA-256 özetini onaltılık dizge olarak döndürür."""
    return hashlib.sha256(data).hexdigest()


def sha256_text(value: str) -> str:
    """Metnin SHA-256 özetini döndürür (UTF-8 kodlamasıyla)."""
    return sha256_bytes(value.encode("utf-8"))


def canonicalize_url(url: str) -> str:
    """URL'i karşılaştırma için kanonik biçime getirir.

    Şema ve alan adı küçük harfe çevrilir, fragment (#...) atılır. Sorgu dizesi
    KORUNUR: Ziraat Katılım'da `?IsArchived=true` parametresi farklı içerik döndürür.

    Args:
        url: Kanonikleştirilecek adres.

    Returns:
        Kanonik URL.
    """
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))


def url_hash(url: str) -> str:
    """URL'in kanonik biçiminin SHA-256 özetini döndürür.

    Args:
        url: Özeti alınacak adres.

    Returns:
        64 karakterlik onaltılık özet.
    """
    return sha256_text(canonicalize_url(url))


def short_hash(value: str, length: int = 16) -> str:
    """Kısaltılmış özet döndürür — dosya adlarında kullanılır.

    Args:
        value: Özeti alınacak metin.
        length: Döndürülecek karakter sayısı.

    Returns:
        Kısaltılmış onaltılık özet.
    """
    return sha256_text(value)[:length]
