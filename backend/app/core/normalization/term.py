"""Vade ve taksit sayısı ayrıştırma.

Vadeler her zaman AY cinsine çevrilerek saklanır; yıl ve gün birimleri aya
dönüştürülür. Bu sayede farklı bankaların "10 yıl", "120 ay" ve "32 gün"
yazımları tek bir sayısal alanda karşılaştırılabilir olur.

GÜN → AY DÖNÜŞÜMÜ YAKLAŞIKTIR: 30 günlük ay kabul edilir ve sonuç en yakın aya
yuvarlanır ("32 günden başlayan" -> 1 ay). Bu bir kayıptır ve bilinçlidir;
gün bazlı vadeler yalnızca katılma hesabı vadelerinde görülür ve ay bazlı
finansman vadeleriyle aynı ölçekte karşılaştırılmaları zaten anlamlı değildir.
Kesin gün değeri gerekiyorsa ham metin `campaign_extractions.value_raw`
alanında korunur.
"""

from __future__ import annotations

import re
from typing import Final

from app.core.normalization.text import lower_tr, normalize_text

# Gün bazlı vadelerin aya çevrilmesinde kullanılan yaklaşık ay uzunluğu.
DAYS_PER_MONTH: Final[int] = 30

# Vade aralığı: "3-36 ay", "6 - 12 ay"
_RANGE_RE: Final[re.Pattern[str]] = re.compile(r"(\d+)\s*-\s*(\d+)\s*(ay|yıl|yil|gün|gun)\w*")

# Tekil vade: "120 ay", "10 yıl", "32 günden"
_SINGLE_RE: Final[re.Pattern[str]] = re.compile(r"(\d+)\s*(ay|yıl|yil|gün|gun)\w*")

# Taksit sayısı: "6 taksit", "4 aya varan taksit", "peşin fiyatına 12 taksit"
_INSTALLMENT_RE: Final[re.Pattern[str]] = re.compile(
    r"(\d+)\s*(?:ay\w*\s*)?(?:varan\s*|kadar\s*)?taksit"
)
# Alternatif yazım: "taksit sayısı: 6"
_INSTALLMENT_LABEL_RE: Final[re.Pattern[str]] = re.compile(
    r"taksit\s*(?:sayısı|adedi)?\s*[:\-]?\s*(\d+)"
)

_UPPER_BOUND_RE: Final[re.Pattern[str]] = re.compile(
    r"kadar|varan|azami|maksimum|en\s+fazla|en\s+çok|üst\s+limit"
)

_LOWER_BOUND_RE: Final[re.Pattern[str]] = re.compile(
    r"başlayan|itibaren|en\s+az|asgari|minimum|ve\s+üzeri|ve\s+üstü|alt\s+limit"
)


def _to_months(value: int, unit: str) -> int:
    """Verilen birimdeki süreyi ay cinsine çevirir.

    Args:
        value: Sayısal süre.
        unit: Birim ("ay", "yıl"/"yil", "gün"/"gun").

    Returns:
        Ay cinsinden süre. Gün dönüşümünde sonuç en az 1'dir.
    """
    if unit in ("yıl", "yil"):
        return value * 12
    if unit in ("gün", "gun"):
        return max(1, round(value / DAYS_PER_MONTH))
    return value


def parse_term_months(text: str | None) -> tuple[int | None, int | None]:
    """Metinden vadeyi ay cinsinden alt/üst sınır olarak çıkarır.

    Örnekler:
        "120 ay"                       -> (120, 120)
        "120 aya kadar"                -> (None, 120)
        "36 aya varan vade"            -> (None, 36)
        "10 yıl"                       -> (120, 120)
        "3-36 ay"                      -> (3, 36)
        "32 günden başlayan vadelerle" -> (1, None)

    Args:
        text: Ayrıştırılacak metin.

    Returns:
        (asgari_ay, azami_ay) ikilisi; vade bulunamazsa (None, None).
    """
    if not text:
        return None, None

    lowered = lower_tr(normalize_text(text))

    range_match = _RANGE_RE.search(lowered)
    if range_match:
        unit = range_match.group(3)
        low = _to_months(int(range_match.group(1)), unit)
        high = _to_months(int(range_match.group(2)), unit)
        return min(low, high), max(low, high)

    single_match = _SINGLE_RE.search(lowered)
    if not single_match:
        return None, None

    months = _to_months(int(single_match.group(1)), single_match.group(2))

    if _UPPER_BOUND_RE.search(lowered):
        return None, months
    if _LOWER_BOUND_RE.search(lowered):
        return months, None
    return months, months


def parse_installment_count(text: str | None) -> int | None:
    """Metinden taksit sayısını çıkarır.

    Örnekler:
        "6 taksit"                 -> 6
        "vade farksız 6 taksit"    -> 6
        "4 aya varan taksit"       -> 4
        "peşin fiyatına 12 taksit" -> 12

    Args:
        text: Ayrıştırılacak metin.

    Returns:
        Taksit sayısı veya bulunamazsa None.
    """
    if not text:
        return None

    lowered = lower_tr(normalize_text(text))

    match = _INSTALLMENT_RE.search(lowered)
    if match:
        return int(match.group(1))

    label_match = _INSTALLMENT_LABEL_RE.search(lowered)
    if label_match:
        return int(label_match.group(1))

    return None
