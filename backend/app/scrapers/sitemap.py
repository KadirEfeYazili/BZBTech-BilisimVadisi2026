"""Sitemap ayrıştırma — keşif için adres listesi çıkarır.

GERÇEK VERİDE ÖĞRENİLENLER (bu davranışların hepsi doğrulandı):

1. **Gzip, `.xml` uzantısıyla servis ediliyor.** Hayat Finans, T.O.M. Bank ve
   Dünya Katılım'da `sitemap.xml` adresi gzip kodlanmış bayt döndürüyor ama
   uzantı `.xml` ve `Content-Type` da çoğu zaman `text/xml`. Uzantıya veya
   başlığa güvenilirse ayrıştırıcı boş liste döndürür — HATA VERMEDEN.
   Bu yüzden içerik magic byte (`\\x1f\\x8b`) ile denetlenir.

2. **Sitemap index'i sitemap sanılıyor.** Birçok banka kök sitemap'te yalnızca
   alt sitemap'lerin adresini veriyor (`<sitemapindex>`). `<urlset>` bekleyen
   bir ayrıştırıcı burada da sessizce boş döner.

3. **Sitemap kırık olabiliyor.** Türkiye Finans'ın sitemap'i 302 ile internet
   şubesi giriş sayfasına yönleniyor; Dünya Katılım'ın robots.txt'i başka bir
   alan adını (blueprint.com.tr, HTTP 403) gösteriyor. Bozuk XML tüm keşfi
   durdurmaz: boş liste döner, çağıran başka bir yönteme geçer.

Bu modül SAFTIR: ağ erişimi yoktur, girdi bayt, çıktı adres listesidir.
Çekme işi `Fetcher`'ındır.
"""

from __future__ import annotations

import gzip
import re
from dataclasses import dataclass
from typing import Final
from xml.etree import ElementTree

from app.logging_config import get_logger
from app.utils.urls import dedupe_urls, is_same_site

logger = get_logger(__name__)

# Gzip akışının ilk iki baytı. Uzantı ve Content-Type yanıltıcı olabildiği
# için tek güvenilir sinyal budur.
GZIP_MAGIC: Final[bytes] = b"\x1f\x8b"

# Sitemap XML'i bu ad alanını kullanır; bazı bankalar hiç kullanmıyor, bazıları
# farklı sürüm yazıyor. Bu yüzden etiket adı ad alanından ARINDIRILARAK
# karşılaştırılır.
TAG_RE: Final[re.Pattern[str]] = re.compile(r"\{.*?\}")


@dataclass
class SitemapEntry:
    """Sitemap'teki tek bir kayıt."""

    loc: str
    lastmod: str | None = None


def is_gzipped(data: bytes) -> bool:
    """İçeriğin gzip olup olmadığını magic byte ile denetler.

    Args:
        data: Ham yanıt gövdesi.

    Returns:
        Gzip akışıysa True.
    """
    return data[:2] == GZIP_MAGIC


def decode_sitemap(data: bytes) -> str:
    """Sitemap gövdesini metne çevirir; gerekiyorsa gzip açar.

    Args:
        data: Ham yanıt gövdesi.

    Returns:
        XML metni; çözülemezse boş dize.
    """
    if not data:
        return ""

    if is_gzipped(data):
        try:
            data = gzip.decompress(data)
        except (OSError, EOFError) as exc:
            # Bozuk gzip tüm keşfi durdurmaz; çağıran başka yönteme geçer.
            logger.warning("sitemap_gzip_acilamadi", hata=str(exc))
            return ""

    # Bankaların bir kısmı UTF-8 dışı bayt bırakıyor; keşif bir karakter
    # yüzünden durmamalı.
    return data.decode("utf-8", errors="replace")


def _local_name(tag: str) -> str:
    """XML etiketinden ad alanını ayıklar (`{ns}url` -> `url`)."""
    return TAG_RE.sub("", tag).lower()


def is_sitemap_index(xml_text: str) -> bool:
    """Belgenin bir sitemap index'i (alt sitemap listesi) olup olmadığını söyler.

    Args:
        xml_text: Sitemap XML metni.

    Returns:
        Kök etiket `sitemapindex` ise True.
    """
    root = _parse(xml_text)
    return root is not None and _local_name(root.tag) == "sitemapindex"


def _parse(xml_text: str) -> ElementTree.Element | None:
    """XML'i ayrıştırır; bozuksa None döndürür."""
    if not xml_text.strip():
        return None
    try:
        return ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        # Kırık sitemap keşfi durdurmaz — belgelenir ve geçilir.
        logger.warning("sitemap_ayristirilamadi", hata=str(exc))
        return None


def parse_sitemap(data: bytes | str) -> list[SitemapEntry]:
    """Sitemap veya sitemap index'inden kayıtları çıkarır.

    Hem `<urlset>` hem `<sitemapindex>` desteklenir; ikisi de `<loc>`
    etiketleri taşır ve çağıran hangisi olduğunu `is_sitemap_index` ile sorar.

    Args:
        data: Ham yanıt gövdesi (gzip olabilir) veya XML metni.

    Returns:
        Bulunan kayıtlar; belge bozuk veya boşsa boş liste.
    """
    xml_text = decode_sitemap(data) if isinstance(data, bytes) else data
    root = _parse(xml_text)
    if root is None:
        return []

    kayitlar: list[SitemapEntry] = []
    for cocuk in root:
        if _local_name(cocuk.tag) not in ("url", "sitemap"):
            continue
        loc: str | None = None
        lastmod: str | None = None
        for alan in cocuk:
            ad = _local_name(alan.tag)
            if ad == "loc" and alan.text:
                loc = alan.text.strip()
            elif ad == "lastmod" and alan.text:
                lastmod = alan.text.strip()
        if loc:
            kayitlar.append(SitemapEntry(loc=loc, lastmod=lastmod))

    return kayitlar


def extract_urls(
    data: bytes | str,
    *,
    same_site_as: str | None = None,
    path_contains: str | None = None,
) -> list[str]:
    """Sitemap'ten adresleri süzerek çıkarır.

    Args:
        data: Ham yanıt gövdesi veya XML metni.
        same_site_as: Verilirse yalnızca bu siteye ait adresler döner
            (`www.` yok sayılarak karşılaştırılır).
        path_contains: Verilirse yalnızca yolunda bu parçayı taşıyan adresler
            döner (ör. "kampanya"). Büyük/küçük harf duyarsız aranır ama
            adresin kendisi DEĞİŞTİRİLMEZ.

    Returns:
        Tekilleştirilmiş adresler, sitemap'teki sırayla.
    """
    adresler = [kayit.loc for kayit in parse_sitemap(data)]

    if same_site_as is not None:
        adresler = [url for url in adresler if is_same_site(url, same_site_as)]

    if path_contains is not None:
        aranan = path_contains.lower()
        adresler = [url for url in adresler if aranan in url.lower()]

    return dedupe_urls(adresler)


def sitemap_urls_from_robots(robots_text: str) -> list[str]:
    """robots.txt içindeki `Sitemap:` satırlarını okur.

    ⚠️ Buradan gelen adres BAŞKA BİR ALAN ADINA işaret edebilir: Dünya
    Katılım'ın robots.txt'i blueprint.com.tr adresini gösteriyor ve o adres
    HTTP 403 döndürüyor. Çağıran, adresin aynı siteye ait olduğunu
    doğrulamalıdır.

    Args:
        robots_text: robots.txt içeriği.

    Returns:
        Bildirilen sitemap adresleri.
    """
    adresler = [
        satir.split(":", 1)[1].strip()
        for satir in robots_text.splitlines()
        if satir.strip().lower().startswith("sitemap:")
    ]
    return dedupe_urls([url for url in adresler if url])
