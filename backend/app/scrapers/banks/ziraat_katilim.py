"""Ziraat Katılım scraper'ı.

⚠️ GİRİŞ NOKTASI SEÇİMİ — üç yol denendi, ikisi çalışmıyor:

  `{BASE}/kampanyalar`            → HTTP 493 (WAF). Kullanılmaz.
  `{BASE}/bireysel/kampanyalar`   → yalnızca 2 tanıtım kartı. Kullanılmaz.
  sitemap'teki `/bireysel/kampanyalar/{slug}` kalıbı → HTTP 493. Kullanılmaz.

Çalışan tek yol 15 KATEGORİ SAYFASINI tek tek gezmektir. Kampanya detayının
kanonik kalıbı ise kategoriden bağımsız olarak `/kart-kampanyalari/{slug}`.

⚠️ HTTP 493 kalıcı hata DEĞİLDİR. Standart dışı bir WAF kodudur; `Fetcher`
onu yeniden denenebilir kabul eder (`RETRYABLE_STATUS_CODES`). Kalıcı hata
sayılırsa banka tamamen boş döner.

🎁 BEDAVA TAKSONOMİ: Bankanın kendi kategori ayrımı 15 sektöre karşılık geliyor.
Kampanya hangi kategori sayfasında bulunduysa o sektör etiketi %100 güvenilir
bir kanıttır; `category_hint` ile taşınır.
"""

from __future__ import annotations

import re
from typing import Final
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from app.core.normalization.date_tr import parse_date_range_tr
from app.core.normalization.text import normalize_text
from app.logging_config import get_logger
from app.processing.cleaner import clean_html, extract_section_text, extract_title
from app.scrapers.base import BaseScraper
from app.scrapers.models import DiscoveredUrl, RawCampaign
from app.utils.slugify import slug_from_url_path
from app.utils.urls import dedupe_urls, is_same_site

logger = get_logger(__name__)

BASE_URL: Final[str] = "https://www.ziraatkatilim.com.tr"

# Bankanın kendi kategori ayrımı. Sıra korunur: pilot çalıştırmada ilk
# kategoriye bakmak yeterli olsun diye "kart-kampanyalari" başta.
CATEGORIES: Final[tuple[str, ...]] = (
    "kart-kampanyalari",
    "kuyum-optik-ve-saat",
    "market-ve-gida",
    "e-ticaret",
    "elektronik-ve-telekomunikasyon",
    "yapi-sektoru-ve-iklimlendirme",
    "akaryakit",
    "diger-kampanyalar",
    "egitim-kitap-ve-kirtasiye",
    "genel-kampanyalar",
    "turizm-ve-seyahat",
    "hobi-ve-oyuncak",
    "mobilya-ve-dekorasyon",
    "beyaz-esya-ve-ev-aletleri",
    "giyim-ve-aksesuar",
)

# Kampanya detay sayfalarının kanonik yol ön eki. Kategori sayfasındaki
# bağlantılar bu kalıba çözülür.
DETAIL_PREFIX: Final[str] = "/kart-kampanyalari/"

# Arşiv (süresi dolmuş kampanyalar) bu parametreyle açılır.
ARCHIVE_QUERY: Final[str] = "?IsArchived=true"

# Ürün sayfaları — oran ve varyant çıkarımında kullanılacak.
PRODUCT_LISTING: Final[str] = f"{BASE_URL}/bireysel/finansman-urunleri"

CONDITION_KEYWORDS: Final[tuple[str, ...]] = (
    "kampanya koşul",
    "koşullar",
    "kampanya detay",
    "katılım koşul",
)

EXCLUSION_KEYWORDS: Final[tuple[str, ...]] = (
    "kampanya dışı",
    "hariç",
    "kapsam dışı",
    "istisna",
)

# "SON GÜN 07.09.2026" gibi ifadeler tarih metninin gövdede ayrı bir rozette
# durduğu durumlarda yakalanır. Ayrıştırma yine `parse_date_range_tr()`'a
# devredilir — scraper içinde tarih regex'i YAZILMAZ (§5 kural 6).
DATE_HINT_RE: Final[re.Pattern[str]] = re.compile(
    r"(son g[üu]n[^.\n]{0,40}|[^.\n]{0,60}tarihinde sona erm[iı][sş]tir)", re.IGNORECASE
)


class ZiraatKatilimScraper(BaseScraper):
    """Ziraat Katılım kampanya scraper'ı."""

    bank_code = "ziraat_katilim"
    version = "1.0.0"

    def discover(self) -> list[DiscoveredUrl]:
        """15 kategori sayfasını ve arşivlerini gezerek kampanya adreslerini toplar.

        `categories` verilmişse yalnızca o kategoriler taranır (pilot
        doğrulama için).

        Returns:
            Keşfedilen kampanya adresleri (tekilleştirilmiş).
        """
        secilen = self._selected_categories()
        discovered: list[DiscoveredUrl] = []
        seen: set[str] = set()

        for kategori in secilen:
            for arsiv in (False, True):
                listing_url = f"{BASE_URL}/kampanyalar/{kategori}"
                if arsiv:
                    listing_url += ARCHIVE_QUERY

                for url in self._campaign_links(listing_url):
                    if url in seen:
                        continue
                    seen.add(url)
                    discovered.append(
                        DiscoveredUrl(
                            url=url,
                            doc_type="campaign",
                            # 🎁 Bankanın kendi kategorisi = sektör kanıtı.
                            category_hint=kategori,
                            segment_hint="bireysel",
                            discovery_method="listing",
                        )
                    )

        return discovered

    def _selected_categories(self) -> tuple[str, ...]:
        """Taranacak kategorileri belirler ve bilinmeyenleri uyarır."""
        if not self.categories:
            return CATEGORIES

        gecerli = tuple(k for k in self.categories if k in CATEGORIES)
        bilinmeyen = set(self.categories) - set(CATEGORIES)
        if bilinmeyen:
            logger.warning(
                "bilinmeyen_kategori",
                banka=self.bank_code,
                kategoriler=sorted(bilinmeyen),
                gecerli_secenekler=list(CATEGORIES),
            )
        return gecerli or CATEGORIES

    def _campaign_links(self, listing_url: str) -> list[str]:
        """Tek bir kategori sayfasından kampanya bağlantılarını çıkarır.

        Args:
            listing_url: Kategori (veya arşiv) listeleme adresi.

        Returns:
            Mutlak kampanya adresleri; sayfa alınamazsa boş liste.
        """
        fetch = self.fetcher.fetch(listing_url)
        if not fetch.is_success or not fetch.html:
            # Tek kategorinin alınamaması diğerlerini durdurmaz.
            logger.warning(
                "kategori_alinamadi",
                banka=self.bank_code,
                url=listing_url,
                durum=fetch.status_code,
                hata=fetch.error,
            )
            return []

        soup = BeautifulSoup(fetch.html, "lxml")
        links: list[str] = []

        for anchor in soup.find_all("a", href=True):
            href = str(anchor["href"]).strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue

            absolute = urljoin(listing_url, href)
            if not is_same_site(absolute, BASE_URL):
                continue

            path = urlsplit(absolute).path
            # ⚠️ Kanonik detay kalıbı yalnızca budur. `/bireysel/kampanyalar/`
            # kalıbı HTTP 493 döndürüyor, izlenmez.
            if not path.startswith(DETAIL_PREFIX):
                continue
            # Kategori kökünün kendisi kampanya değildir.
            if path.rstrip("/") == DETAIL_PREFIX.rstrip("/"):
                continue

            links.append(absolute)

        return dedupe_urls(links)

    def parse_detail(self, html: str, url: str, hint: DiscoveredUrl) -> RawCampaign | None:
        """Kampanya detay sayfasını ayrıştırır.

        Args:
            html: Detay sayfasının HTML'i.
            url: Sayfanın adresi.
            hint: Keşiften gelen kategori ve segment bilgisi.

        Returns:
            Çıkarılan kampanya; başlık bulunamazsa None.
        """
        title = extract_title(html)
        if not title:
            return None

        body_text = clean_html(html)
        conditions = extract_section_text(html, CONDITION_KEYWORDS)
        exclusions = extract_section_text(html, EXCLUSION_KEYWORDS)

        start_date, end_date, precision = self._parse_dates(conditions, body_text)

        return RawCampaign(
            # ⚠️ Slug href'ten birebir okunur. Sondaki `-1`, `-2` ekleri yeni
            # dönem yayınlarını ayırt eder ve KORUNUR.
            external_slug=slug_from_url_path(url),
            title=title,
            source_url=url,
            description=self._first_paragraph(body_text),
            conditions_text=conditions,
            exclusions_text=exclusions,
            # Sınıflandırma ayrı bir adımda yapılır; burada yalnızca bankanın
            # kendi kategorisi kanıt olarak taşınır.
            category=None,
            segment=hint.segment_hint,
            start_date=start_date,
            end_date=end_date,
            date_precision=precision,
            # Yalnızca `?IsArchived=true` sayfasından gelenler arşivdir.
            is_archived=ARCHIVE_QUERY.lstrip("?") in urlsplit(url).query,
        )

    @staticmethod
    def _parse_dates(conditions: str | None, body_text: str) -> tuple[object, object, str]:
        """Üç farklı tarih biçimini normalizasyon kütüphanesine devreder.

        Ziraat'te üç biçim gözlendi ve üçü de `parse_date_range_tr()` ile
        çözülür — scraper içinde tarih regex'i yazılmaz:
            "Son Gün 07.09.2026"              -> yalnızca bitiş, `partial`
            "10 Temmuz – 7 Ağustos 2026"      -> başlangıç yılı bitişten devralınır
            "07-08-2026 Tarihinde Sona Ermiştir" -> tire ayraçlı

        Önce koşul metni taranır: gövdede başka tarihler (yayın tarihi,
        duyuru tarihi) bulunabiliyor ve yanlış eşleşme üretiyor.

        Returns:
            (başlangıç, bitiş, kesinlik).
        """
        for kaynak in (conditions or "", body_text):
            if not kaynak:
                continue
            start, end, precision = parse_date_range_tr(kaynak)
            if precision != "unknown":
                return start, end, precision

        # Tarih rozetteki kısa ifadede kalmış olabilir.
        eslesme = DATE_HINT_RE.search(body_text)
        if eslesme:
            start, end, precision = parse_date_range_tr(eslesme.group(0))
            if precision != "unknown":
                return start, end, precision

        # ⚠️ Bulunamadıysa UYDURULMAZ: NULL kalır, durum `unknown` olur.
        return None, None, "unknown"

    @staticmethod
    def _first_paragraph(text: str, *, max_length: int = 500) -> str | None:
        """Gövde metninin ilk anlamlı paragrafını açıklama olarak döndürür."""
        for line in text.split("\n"):
            candidate = normalize_text(line)
            if len(candidate) >= 40:
                return candidate[:max_length]
        return None
