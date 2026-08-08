"""Türkçe finansal metin normalizasyonu.

Bu paket, banka sayfalarındaki serbest metni karşılaştırılabilir sayısal ve
tarihsel değerlere çeviren saf fonksiyonlardan oluşur. Hiçbir fonksiyonun yan
etkisi yoktur; veritabanı, ağ veya dosya sistemine erişmez.
"""

from app.core.normalization.date_tr import (
    TURKISH_MONTHS,
    parse_date_range_tr,
    parse_date_tr,
)
from app.core.normalization.money import (
    DEFAULT_CURRENCY,
    detect_currency,
    parse_decimal_tr,
    parse_money,
    parse_money_range,
    parse_tier_structure,
)
from app.core.normalization.rate import parse_rate, parse_rate_range
from app.core.normalization.term import parse_installment_count, parse_term_months
from app.core.normalization.text import (
    ascii_fold_tr,
    collapse_whitespace,
    lower_tr,
    normalize_text,
    strip_boilerplate,
    strip_tags,
)

__all__ = [
    "DEFAULT_CURRENCY",
    "TURKISH_MONTHS",
    "ascii_fold_tr",
    "collapse_whitespace",
    "detect_currency",
    "lower_tr",
    "normalize_text",
    "parse_date_range_tr",
    "parse_date_tr",
    "parse_decimal_tr",
    "parse_installment_count",
    "parse_money",
    "parse_money_range",
    "parse_rate",
    "parse_rate_range",
    "parse_term_months",
    "parse_tier_structure",
    "strip_boilerplate",
    "strip_tags",
]
