"""Türkçe tarih ayrıştırma — projedeki en kritik ve en kırılgan modül.

Bankaların kampanya sayfalarında tarih YAPISAL bir alanda durmuyor; serbest metin
içine gömülü ve her bankada farklı yazılıyor. Analizde doğrulanan biçimler:

    1. 01.01.2026 - 31.12.2026                    (Albaraka)
    2. 6.08.2026 - 31.12.2026                     (tek haneli gün)
    3. 6 Ağustos 2026 - 31 Aralık 2026            (Ziraat Katılım)
    4. 1-31 Ağustos 2026                          (gün aralığı, ay/yıl ortak)
    5. 10 Temmuz - 7 Ağustos 2026                 (başlangıçta yıl YOK)
    6. Son Gün 31.12.2026                         (yalnızca bitiş)
    7. 07-08-2026 Tarihinde Sona Ermiştir         (tire ayırıcı, yalnızca bitiş)

TASARIM KARARI — TAHMİN YOK: Metinde işaretsiz tek bir tarih varsa
(None, None, "unknown") döner. Gerekçe: kampanya metinlerinde kampanya süresiyle
ilgisi olmayan tarihler bulunuyor (ör. Emlak Katılım'da "kullanılmayan puanlar
15 Ekim 2026 tarihinde geri alınacaktır"). İşaretsiz tarihi bitiş kabul etmek
kampanyayı yanlış tarihle etiketlerdi. Eksik veri, yanlış veriden iyidir.

`date_precision` alanının anlamı:
    exact    — başlangıç ve bitiş metinde açıkça yazılı
    partial  — yalnızca biri yazılı
    inferred — bir bilgi çıkarsandı (ör. başlangıcın yılı bitişten devralındı)
    unknown  — tarih bulunamadı
"""

from __future__ import annotations

import re
from datetime import date
from typing import Final

from app.core.normalization.text import ascii_fold_tr, lower_tr, normalize_text

# Türkçe ay adları. ASCII yazımlar (agustos, subat ...) otomatik olarak eklenir;
# banka metinlerinde her iki yazıma da rastlanıyor.
TURKISH_MONTHS: Final[dict[str, int]] = {
    "ocak": 1,
    "şubat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "eylül": 9,
    "ekim": 10,
    "kasım": 11,
    "aralık": 12,
}

# Kısaltmalar — bazı sayfalarda "1 Oca 2026" biçimi görülüyor.
TURKISH_MONTH_ABBREVIATIONS: Final[dict[str, int]] = {
    "oca": 1,
    "şub": 2,
    "mar": 3,
    "nis": 4,
    "may": 5,
    "haz": 6,
    "tem": 7,
    "ağu": 8,
    "eyl": 9,
    "eki": 10,
    "kas": 11,
    "ara": 12,
}


def _build_month_lookup() -> dict[str, int]:
    """Ay adı → ay numarası sözlüğünü ASCII yazımlarla birlikte kurar."""
    lookup: dict[str, int] = {}
    for source in (TURKISH_MONTHS, TURKISH_MONTH_ABBREVIATIONS):
        for name, number in source.items():
            lookup[name] = number
            lookup[ascii_fold_tr(name)] = number
    return lookup


MONTH_LOOKUP: Final[dict[str, int]] = _build_month_lookup()

# Uzun adlar önce denenmeli: "ağustos" kalıbı "ağu" kalıbından önce gelmeli.
_MONTH_ALT: Final[str] = "|".join(
    re.escape(name) for name in sorted(MONTH_LOOKUP, key=len, reverse=True)
)

# Gün ve yıl grupları: daha uzun bir sayının parçası olmadıklarından emin olunur
# (ör. "2026" içindeki "20" gün olarak yorumlanmamalı).
_D = r"(?<!\d)(\d{1,2})(?!\d)"
_Y = r"(?<!\d)(\d{4})(?!\d)"

# Sayısal tarih: 01.01.2026 · 6.08.2026 · 07-08-2026 · 01/01/2026
_DATE_NUM_PATTERN: Final[str] = r"(?<!\d)(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})(?!\d)"
# Türkçe ay adlı tarih: 6 Ağustos 2026
_DATE_TR_PATTERN: Final[str] = (
    rf"(?<!\d)(\d{{1,2}})(?!\d)\s+(?:{_MONTH_ALT})\s+(?<!\d)(\d{{4}})(?!\d)"
)
# İşaretleyici kalıplarında kullanılan "herhangi bir tarih" ifadesi (grup yakalamaz).
_DATE_ANY: Final[str] = (
    rf"(?:(?:\d{{1,2}}[.\-/]\d{{1,2}}[.\-/]\d{{4}})|(?:\d{{1,2}}\s+(?:{_MONTH_ALT})\s+\d{{4}}))"
)

_DATE_NUM_RE: Final[re.Pattern[str]] = re.compile(_DATE_NUM_PATTERN)
_DATE_TR_RE: Final[re.Pattern[str]] = re.compile(_DATE_TR_PATTERN)

# "saat 00.01" gibi ifadeler tarih kalıplarını böler; ayrıştırmadan önce çıkarılır.
_TIME_RE: Final[re.Pattern[str]] = re.compile(r"\s*saat\s*\d{1,2}[.:]\d{2}(?::\d{2})?")

# ── Aralık kalıpları (en özgülden genele) ─────────────────

# 1-2. Sayısal aralık: "01.01.2026 - 31.12.2026"
_RANGE_NUM_RE: Final[re.Pattern[str]] = re.compile(
    rf"{_DATE_NUM_PATTERN}\s*-\s*{_DATE_NUM_PATTERN}"
)

# 3. Türkçe aylı aralık, iki yıl da yazılı: "6 Ağustos 2026 - 31 Aralık 2026"
_RANGE_TR_FULL_RE: Final[re.Pattern[str]] = re.compile(
    rf"{_D}\s+({_MONTH_ALT})\s+{_Y}\s*-\s*{_D}\s+({_MONTH_ALT})\s+{_Y}"
)

# 5. Başlangıçta yıl yok: "10 Temmuz - 7 Ağustos 2026" -> yıl bitişten devralınır
_RANGE_TR_NO_START_YEAR_RE: Final[re.Pattern[str]] = re.compile(
    rf"{_D}\s+({_MONTH_ALT})\s*-\s*{_D}\s+({_MONTH_ALT})\s+{_Y}"
)

# 4. Gün aralığı, ay ve yıl ortak: "1-31 Ağustos 2026"
_RANGE_TR_DAY_ONLY_RE: Final[re.Pattern[str]] = re.compile(
    rf"{_D}\s*-\s*{_D}\s+({_MONTH_ALT})\s+{_Y}"
)

# ── İşaretleyici kalıpları ────────────────────────────────

# 6-7. Yalnızca bitiş bildiren ifadeler.
_END_MARKER_RES: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern)
    for pattern in (
        rf"son\s+gün\w*\s*:?\s*({_DATE_ANY})",
        rf"({_DATE_ANY})\s*tarihinde\s+sona\s+er",
        rf"({_DATE_ANY})\s*tarihine\s+kadar",
        rf"({_DATE_ANY})\s*['’]?\w*\s+kadar",
        rf"bitiş\s*(?:tarihi)?\s*:?\s*({_DATE_ANY})",
        rf"kampanya\s+bitiş\w*\s*:?\s*({_DATE_ANY})",
        rf"son\s+katılım\w*\s*:?\s*({_DATE_ANY})",
    )
)

# Yalnızca başlangıç bildiren ifadeler.
_START_MARKER_RES: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern)
    for pattern in (
        rf"({_DATE_ANY})\s*(?:tarihinden\s+)?itibaren",
        rf"({_DATE_ANY})\s*tarihinde\s+başla",
        rf"başlangıç\s*(?:tarihi)?\s*:?\s*({_DATE_ANY})",
        rf"kampanya\s+başlangıç\w*\s*:?\s*({_DATE_ANY})",
    )
)


def _safe_date(year: int, month: int, day: int) -> date | None:
    """Geçerliyse tarih nesnesi üretir, değilse None döner.

    Args:
        year: Yıl.
        month: Ay (1-12).
        day: Gün.

    Returns:
        Geçerli tarih veya None (ör. 31.02.2026 için None).
    """
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _month_number(name: str) -> int | None:
    """Ay adını numaraya çevirir (Türkçe ve ASCII yazımı destekler)."""
    return MONTH_LOOKUP.get(name)


def _prepare(text: str) -> str:
    """Metni tarih ayrıştırmaya hazırlar: normalize eder, saat ifadelerini atar."""
    prepared = lower_tr(normalize_text(text))
    return _TIME_RE.sub(" ", prepared)


def parse_date_tr(text: str | None) -> date | None:
    """Metindeki ilk geçerli tarihi döndürür.

    Hem sayısal (01.01.2026, 07-08-2026) hem Türkçe ay adlı (6 Ağustos 2026)
    yazımı destekler.

    Args:
        text: Ayrıştırılacak metin.

    Returns:
        Bulunan ilk geçerli tarih veya None.
    """
    if not text:
        return None

    prepared = _prepare(text)

    candidates: list[tuple[int, date]] = []

    for match in _DATE_NUM_RE.finditer(prepared):
        parsed = _safe_date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        if parsed:
            candidates.append((match.start(), parsed))

    for match in _DATE_TR_RE.finditer(prepared):
        month = _month_number(match.group(0).split()[1])
        if month is None:
            continue
        parsed = _safe_date(int(match.group(2)), month, int(match.group(1)))
        if parsed:
            candidates.append((match.start(), parsed))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _match_marker(patterns: tuple[re.Pattern[str], ...], prepared: str) -> date | None:
    """İşaretleyici kalıplarından ilk eşleşenin tarihini döndürür."""
    for pattern in patterns:
        match = pattern.search(prepared)
        if match:
            parsed = parse_date_tr(match.group(1))
            if parsed:
                return parsed
    return None


def parse_date_range_tr(text: str | None) -> tuple[date | None, date | None, str]:
    """Metinden kampanya tarih aralığını ve çıkarım kesinliğini döndürür.

    Örnekler:
        "01.01.2026 - 31.12.2026"              -> (2026-01-01, 2026-12-31, "exact")
        "6 Ağustos 2026 - 31 Aralık 2026"      -> (2026-08-06, 2026-12-31, "exact")
        "1-31 Ağustos 2026"                    -> (2026-08-01, 2026-08-31, "exact")
        "10 Temmuz - 7 Ağustos 2026"           -> (2026-07-10, 2026-08-07, "inferred")
        "Son Gün 31.12.2026"                   -> (None, 2026-12-31, "partial")
        "07-08-2026 Tarihinde Sona Ermiştir"   -> (None, 2026-08-07, "partial")
        "Kampanya devam ediyor"                -> (None, None, "unknown")

    Args:
        text: Ayrıştırılacak metin.

    Returns:
        (başlangıç, bitiş, kesinlik) üçlüsü.
    """
    if not text:
        return None, None, "unknown"

    prepared = _prepare(text)

    # 1-2. Sayısal aralık — en kesin biçim.
    match = _RANGE_NUM_RE.search(prepared)
    if match:
        start = _safe_date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        end = _safe_date(int(match.group(6)), int(match.group(5)), int(match.group(4)))
        if start and end:
            return start, end, "exact"

    # 3. Türkçe aylı aralık, iki yıl da yazılı.
    match = _RANGE_TR_FULL_RE.search(prepared)
    if match:
        start_month = _month_number(match.group(2))
        end_month = _month_number(match.group(5))
        if start_month and end_month:
            start = _safe_date(int(match.group(3)), start_month, int(match.group(1)))
            end = _safe_date(int(match.group(6)), end_month, int(match.group(4)))
            if start and end:
                return start, end, "exact"

    # 4. Gün aralığı, ay ve yıl ortak: "1-31 Ağustos 2026"
    match = _RANGE_TR_DAY_ONLY_RE.search(prepared)
    if match:
        month = _month_number(match.group(3))
        if month:
            year = int(match.group(4))
            start = _safe_date(year, month, int(match.group(1)))
            end = _safe_date(year, month, int(match.group(2)))
            if start and end:
                return start, end, "exact"

    # 5. Başlangıçta yıl yok — yıl bitişten devralınır, bu bir ÇIKARIMDIR.
    match = _RANGE_TR_NO_START_YEAR_RE.search(prepared)
    if match:
        start_month = _month_number(match.group(2))
        end_month = _month_number(match.group(4))
        if start_month and end_month:
            year = int(match.group(5))
            start = _safe_date(year, start_month, int(match.group(1)))
            end = _safe_date(year, end_month, int(match.group(3)))
            if start and end:
                # Başlangıç bitişten sonraysa kampanya yıl sınırını aşıyor demektir.
                if start > end:
                    start = _safe_date(year - 1, start_month, int(match.group(1)))
                if start:
                    return start, end, "inferred"

    # 6-7. İşaretleyici bazlı: başlangıç ve bitiş ayrı ayrı aranır.
    start_marked = _match_marker(_START_MARKER_RES, prepared)
    end_marked = _match_marker(_END_MARKER_RES, prepared)

    if start_marked and end_marked:
        return start_marked, end_marked, "exact"
    if end_marked:
        return None, end_marked, "partial"
    if start_marked:
        return start_marked, None, "partial"

    # İşaretsiz tek tarih TAHMİN EDİLMEZ — bkz. modül başlığındaki tasarım kararı.
    return None, None, "unknown"
