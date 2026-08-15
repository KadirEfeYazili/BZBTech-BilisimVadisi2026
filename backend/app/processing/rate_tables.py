"""Yapısal kâr payı oranı tablolarının ayrıştırılması.

Bankaların bir kısmı oranı serbest metinde değil, gerçek bir HTML tablosunda
yayımlıyor. Bu tablolar veri setinin EN GÜVENİLİR parçasıdır: bankanın kendi
yayımladığı sayıdır, çıkarım değildir (`rate_source='html_table'`, güven 1.00).

⚠️ `pandas.read_html` KULLANILMAZ. Türkiye Finans'ın tablo başlıklarında
kelimenin İÇİNDE zero-width space (U+200B) ve non-breaking space (U+00A0) var:

    '\\u200bVa\\u200bde'   'Kâr \\u200bPayı\\u00a0Oranı'

`read_html` bu başlıkları olduğu gibi kolon adı yapar ve kolon eşleştirmesi
HATA VERMEDEN başarısız olur. Ayrıştırma elle, `normalize_text()` üzerinden
yapılır.

⚠️ VARYANT BOYUTU TABLONUN DIŞINDADIR. Türkiye Finans aynı sayfada iki tablo
yayımlıyor ve hangisinin hangisi olduğu tablonun ÜSTÜNDEKİ başlıkta yazılı:

    "Sigortalı İhtiyaç Finansmanı ... Kâr Payı Oranları ve Maliyet Tablosu"
    "Sigortasız İhtiyaç Finansmanı ... Kâr Payı Oranları ve Maliyet Tablosu"

Başlık okunmazsa iki tablo tek ürüne ait sanılır ve sigortalı oran sigortasız
oranla karışır — "en düşük kâr payı" karşılaştırması yanlış çıkar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from bs4 import BeautifulSoup, Tag

from app.core.normalization.rate import parse_rate
from app.core.normalization.term import parse_term_months
from app.core.normalization.text import ascii_fold_tr, lower_tr, normalize_text

# Kolon başlığı → alan adı. Eşleştirme katlanmış metinle yapılır.
COLUMN_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "term_months": ("vade",),
    "profit_rate_pct": ("kar payi orani", "kar payi", "oran"),
    "allocation_fee_pct": ("tahsis ucreti", "tahsis"),
    "monthly_cost_pct": ("aylik toplam maliyet", "aylik maliyet"),
    "annual_cost_pct": ("yillik toplam maliyet", "yillik maliyet"),
}

# Tablonun üstündeki başlıkta aranan varyant ifadeleri.
VARIANT_MARKERS: Final[tuple[tuple[str, str], ...]] = (
    # ⚠️ SIRA ÖNEMLİ: "sigortasız" içinde "sigortalı" GEÇMEZ ama ters yönde
    # kısmi eşleşme riski var; uzun olan önce denenir.
    ("sigortasiz", "sigortasiz"),
    ("sigortali", "sigortali"),
    ("enerji sinifi a", "enerji_a"),
    ("enerji sinifi b", "enerji_b"),
    ("sifir konut", "sifir_konut"),
    ("ikinci el konut", "ikinci_el_konut"),
    ("sifir arac", "sifir_arac"),
    ("ikinci el arac", "ikinci_el_arac"),
)

# Başlık aramasında tablodan geriye kaç metin düğümü taranacak.
_HEADING_LOOKBACK: Final[int] = 12

# Bir satırın veri satırı sayılması için gereken en az dolu hücre.
_MIN_FILLED_CELLS: Final[int] = 2


@dataclass(frozen=True)
class RateRow:
    """Oran tablosunun tek bir satırı."""

    term_months: int | None = None
    profit_rate_pct: Decimal | None = None
    allocation_fee_pct: Decimal | None = None
    monthly_cost_pct: Decimal | None = None
    annual_cost_pct: Decimal | None = None
    evidence_text: str | None = None


@dataclass(frozen=True)
class RateTable:
    """Tek bir oran tablosu ve ait olduğu varyant."""

    rows: tuple[RateRow, ...]
    variant_key: str | None = None
    variant_label: str | None = None
    caption: str | None = None

    @property
    def is_empty(self) -> bool:
        """Hiç veri satırı çıkarılamadı mı?"""
        return not self.rows


def _fold(text: str | None) -> str:
    """Karşılaştırma için metni sadeleştirir (görünmez karakterler dahil)."""
    return ascii_fold_tr(lower_tr(normalize_text(text or "")))


def _cells(row: Tag) -> list[str]:
    """Satırdaki hücrelerin normalize edilmiş metnini döndürür."""
    return [normalize_text(c.get_text(separator=" ")) for c in row.find_all(["th", "td"])]


def _map_columns(header: list[str]) -> dict[int, str]:
    """Başlık satırından kolon indeksi → alan adı eşlemesi üretir.

    ⚠️ Eşleştirme KATLANMIŞ metinle yapılır; ham dize karşılaştırması
    zero-width karakterler yüzünden sessizce başarısız olur.
    """
    esleme: dict[int, str] = {}
    for indeks, baslik in enumerate(header):
        katlanmis = _fold(baslik)
        if not katlanmis:
            continue
        for alan, adlar in COLUMN_ALIASES.items():
            if alan in esleme.values():
                continue
            if any(ad in katlanmis for ad in adlar):
                esleme[indeks] = alan
                break
    return esleme


def _table_caption(table: Tag) -> str | None:
    """Tablonun üstündeki açıklayıcı başlığı bulur.

    Önce `<caption>`, sonra tablodan geriye doğru en yakın anlamlı metin.
    Varyant boyutu (sigortalı/sigortasız) burada yazılı.
    """
    caption = table.find("caption")
    if caption is not None:
        metin = normalize_text(caption.get_text(separator=" "))
        if metin:
            return metin

    node = table
    for _ in range(_HEADING_LOOKBACK):
        node = node.find_previous(string=True)  # type: ignore[assignment]
        if node is None:
            break
        metin = normalize_text(str(node))
        # Sayı ağırlıklı kısa parçalar tablo hücreleridir, başlık değil.
        if len(metin) >= 20 and not re.fullmatch(r"[\d.,%\s]+", metin):
            return metin
    return None


def _variant_from_caption(caption: str | None) -> tuple[str | None, str | None]:
    """Başlıktan varyant anahtarını çıkarır.

    Returns:
        (kanonik_anahtar, ham_etiket); bulunamazsa (None, None).
    """
    if not caption:
        return None, None

    katlanmis = _fold(caption)
    for isaret, anahtar in VARIANT_MARKERS:
        if isaret in katlanmis:
            return anahtar, caption
    return None, None


def _term_months(raw: str) -> int | None:
    """Vade hücresini ay sayısına çevirir.

    ⚠️ Oran tablolarında vade çoğu zaman BİRİMSİZ yazılıyor ("3", "36").
    `parse_term_months()` birim arayıp bulamayınca `(None, None)` döndürüyor;
    tek başına kullanılırsa tablonun vade kolonu tamamen boş kalır.
    """
    temiz = raw.strip()
    if temiz.isdigit():
        return int(temiz)

    alt, ust = parse_term_months(temiz)
    # Tek satır tek vadeyi temsil eder; aralık gelirse üst sınır kullanılır.
    return ust if ust is not None else alt


def _parse_row(cells: list[str], columns: dict[int, str]) -> RateRow | None:
    """Veri satırını `RateRow`'a çevirir; veri yoksa None."""
    degerler: dict[str, object] = {}

    for indeks, alan in columns.items():
        if indeks >= len(cells):
            continue
        ham = cells[indeks]
        if not ham:
            continue

        if alan == "term_months":
            degerler[alan] = _term_months(ham)
        else:
            # ⚠️ Türkçe ondalık ayracı: "%4,20" -> 4.20
            degerler[alan] = parse_rate(ham)

    dolu = [d for d in degerler.values() if d is not None]
    if len(dolu) < _MIN_FILLED_CELLS:
        return None

    return RateRow(
        term_months=degerler.get("term_months"),  # type: ignore[arg-type]
        profit_rate_pct=degerler.get("profit_rate_pct"),  # type: ignore[arg-type]
        allocation_fee_pct=degerler.get("allocation_fee_pct"),  # type: ignore[arg-type]
        monthly_cost_pct=degerler.get("monthly_cost_pct"),  # type: ignore[arg-type]
        annual_cost_pct=degerler.get("annual_cost_pct"),  # type: ignore[arg-type]
        evidence_text=" | ".join(c for c in cells if c)[:300],
    )


def parse_rate_tables(html: str | None) -> list[RateTable]:
    """Sayfadaki tüm kâr payı oranı tablolarını ayrıştırır.

    Args:
        html: Ürün sayfasının ham HTML'i.

    Returns:
        Bulunan tablolar; oran kolonu taşımayan tablolar atlanır.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    tablolar: list[RateTable] = []

    for table in soup.find_all("table"):
        satirlar = table.find_all("tr")
        if len(satirlar) < 2:
            continue

        basliklar = _cells(satirlar[0])
        kolonlar = _map_columns(basliklar)

        # Oran kolonu yoksa bu bir oran tablosu değildir (ör. ücret listesi).
        if "profit_rate_pct" not in kolonlar.values():
            continue

        veri: list[RateRow] = []
        for satir in satirlar[1:]:
            ayristirilan = _parse_row(_cells(satir), kolonlar)
            if ayristirilan is not None:
                veri.append(ayristirilan)

        if not veri:
            continue

        caption = _table_caption(table)
        anahtar, etiket = _variant_from_caption(caption)
        tablolar.append(
            RateTable(
                rows=tuple(veri),
                variant_key=anahtar,
                variant_label=etiket,
                caption=caption,
            )
        )

    return tablolar
