"""Türkçe finansal metin normalizasyonu — temel metin katmanı.

Bu modül diğer tüm ayrıştırıcıların ön işlemcisidir. Buradaki en kritik davranış
GÖRÜNMEZ karakterlerin temizlenmesidir: Türkiye Finans'ın oran tablosu
başlıklarında gerçekten zero-width space ve non-breaking space bulunuyor.
Temizlenmezse kolon eşleştirmesi SESSİZCE başarısız olur — hata fırlatmaz,
sadece yanlış veri üretir.

Türkçe karakterler (ı İ ş Ş ğ Ğ ü Ü ö Ö ç Ç â) HİÇBİR koşulda ASCII'ye çevrilmez;
ASCII katlama yalnızca karşılaştırma amaçlı ayrı bir fonksiyonda yapılır.

TASARIM NOTU: Görünmez karakter sabitleri kaynak koda birebir yazılmaz, kod
noktalarından `chr()` ile üretilir. Birebir yazılsalardı editörde görünmez olur,
kopyalama sırasında sessizce kaybolur ve modül işlevini yitirirdi. Bu biçimde
kaynak dosya tamamen ASCII kalır ve hangi karakterin neden temizlendiği okunur.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Final

# ── Görünmez / sıfır genişlikli karakterler ───────────────
ZERO_WIDTH_CODEPOINTS: Final[tuple[int, ...]] = (
    0x200B,  # ZERO WIDTH SPACE — Türkiye Finans tablo başlıklarında bulunuyor
    0x200C,  # ZERO WIDTH NON-JOINER
    0x200D,  # ZERO WIDTH JOINER
    0x2060,  # WORD JOINER
    0xFEFF,  # ZERO WIDTH NO-BREAK SPACE (BOM)
    0x00AD,  # SOFT HYPHEN
    0x180E,  # MONGOLIAN VOWEL SEPARATOR
)

# ── Boşluk benzeri karakterler → normal boşluk ────────────
UNICODE_SPACE_CODEPOINTS: Final[tuple[int, ...]] = (
    0x00A0,  # NO-BREAK SPACE — en yaygın olanı
    0x1680,  # OGHAM SPACE MARK
    0x2000,  # EN QUAD
    0x2001,  # EM QUAD
    0x2002,  # EN SPACE
    0x2003,  # EM SPACE
    0x2004,  # THREE-PER-EM SPACE
    0x2005,  # FOUR-PER-EM SPACE
    0x2006,  # SIX-PER-EM SPACE
    0x2007,  # FIGURE SPACE
    0x2008,  # PUNCTUATION SPACE
    0x2009,  # THIN SPACE
    0x200A,  # HAIR SPACE
    0x202F,  # NARROW NO-BREAK SPACE
    0x205F,  # MEDIUM MATHEMATICAL SPACE
    0x3000,  # IDEOGRAPHIC SPACE
)

# ── Tire benzeri karakterler → düz tire ───────────────────
# Tarih aralıklarında en-dash (U+2013) ve em-dash (U+2014) çok yaygın:
# "10 Temmuz <en-dash> 7 Ağustos 2026". Tek biçime indirilmezse aralık
# regex'leri eşleşmeyi kaçırır ve tarih bulunamaz.
DASH_CODEPOINTS: Final[tuple[int, ...]] = (
    0x2010,  # HYPHEN
    0x2011,  # NON-BREAKING HYPHEN
    0x2012,  # FIGURE DASH
    0x2013,  # EN DASH
    0x2014,  # EM DASH
    0x2015,  # HORIZONTAL BAR
    0x2212,  # MINUS SIGN
    0x2043,  # HYPHEN BULLET
    0xFE58,  # SMALL EM DASH
    0xFE63,  # SMALL HYPHEN-MINUS
    0xFF0D,  # FULLWIDTH HYPHEN-MINUS
)

ZERO_WIDTH_CHARS: Final[str] = "".join(chr(cp) for cp in ZERO_WIDTH_CODEPOINTS)
UNICODE_SPACES: Final[str] = "".join(chr(cp) for cp in UNICODE_SPACE_CODEPOINTS)
DASH_CHARS: Final[str] = "".join(chr(cp) for cp in DASH_CODEPOINTS)

# Türkçe küçük harfe çevirmede özel eşlemeler.
# Python'un str.lower() metodu 'İ' harfini 'i' + birleşen nokta (U+0307) olarak
# çevirir; bu, anahtar kelime eşleştirmesini bozar.
_TR_LOWER_MAP: Final[dict[int, str]] = str.maketrans({"İ": "i", "I": "ı"})

# ASCII katlama eşlemesi — YALNIZCA karşılaştırma için (ör. "agustos" ↔ "ağustos").
# Görüntülenecek metinlerde ASLA kullanılmaz.
_ASCII_FOLD_MAP: Final[dict[int, str]] = str.maketrans(
    {
        "ı": "i",
        "İ": "I",
        "ş": "s",
        "Ş": "S",
        "ğ": "g",
        "Ğ": "G",
        "ü": "u",
        "Ü": "U",
        "ö": "o",
        "Ö": "O",
        "ç": "c",
        "Ç": "C",
        "â": "a",
        "Â": "A",
        "î": "i",
        "Î": "I",
        "û": "u",
        "Û": "U",
    }
)

_ZERO_WIDTH_RE: Final[re.Pattern[str]] = re.compile(f"[{ZERO_WIDTH_CHARS}]")
_SPACE_RE: Final[re.Pattern[str]] = re.compile(f"[{UNICODE_SPACES}]")
_DASH_RE: Final[re.Pattern[str]] = re.compile(f"[{DASH_CHARS}]")
_MULTISPACE_RE: Final[re.Pattern[str]] = re.compile(r"[ \t\f\v]+")
_MULTINEWLINE_RE: Final[re.Pattern[str]] = re.compile(r"\n{3,}")
_TAG_RE: Final[re.Pattern[str]] = re.compile(r"<[^>]+>")

# Bankaların her sayfasında tekrarlayan, kampanya metniyle ilgisi olmayan bloklar.
# Dünya Katılım'da bu metinler kampanya içeriğinden daha uzun olabiliyor.
_BOILERPLATE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"çerez(ler)?\s+(politika|aydınlatma|kullanım|tercih|ayar)",
        r"cookie\s+(policy|consent)",
        r"kvkk|kişisel\s+verilerin\s+korunması",
        r"aydınlatma\s+metni",
        r"gizlilik\s+(bildirimi|politikası)",
        r"tüm\s+hakları\s+saklıdır",
        r"bilgi\s+toplumu\s+hizmetleri",
        r"müşteri\s+hizmetleri\s*:?\s*0\d{3}",
        r"sosyal\s+medya\s+hesap",
        r"mobil\s+uygulamayı\s+indir",
        r"app\s*store|google\s*play",
        r"sitede\s+gezinmeye\s+devam\s+ederek",
        r"tarayıcı\s+ayarlarınız",
    )
)


def lower_tr(value: str) -> str:
    """Türkçe kurallarına uygun küçük harfe çevirir.

    `str.lower()` 'İ' harfini 'i' + birleşen nokta olarak çevirdiği için anahtar
    kelime eşleştirmesinde doğrudan kullanılamaz.

    Args:
        value: Çevrilecek metin.

    Returns:
        Küçük harfe çevrilmiş metin.
    """
    return value.translate(_TR_LOWER_MAP).lower()


def ascii_fold_tr(value: str) -> str:
    """Türkçe karakterleri ASCII karşılıklarına katlar — SADECE karşılaştırma için.

    Gerekçe: banka metinlerinde ay adları hem "Ağustos" hem "Agustos" biçiminde
    geçebiliyor. Bu fonksiyon iki yazımı aynı anahtara indirir.

    UYARI: Kullanıcıya gösterilecek veya veritabanına yazılacak metinlerde
    kullanılmaz — Türkçe karakterler korunmalıdır.

    Args:
        value: Katlanacak metin.

    Returns:
        ASCII'ye katlanmış metin.
    """
    return value.translate(_ASCII_FOLD_MAP)


def collapse_whitespace(value: str) -> str:
    """Fazla boşlukları tek boşluğa indirir, satır başı/sonu boşluklarını kırpar.

    Satır yapısı korunur (en fazla iki ardışık satır sonu) — kampanya koşullarının
    madde yapısı kaybolmasın diye.

    Args:
        value: İşlenecek metin.

    Returns:
        Boşlukları düzenlenmiş metin.
    """
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = _MULTISPACE_RE.sub(" ", value)
    value = "\n".join(line.strip() for line in value.split("\n"))
    value = _MULTINEWLINE_RE.sub("\n\n", value)
    return value.strip()


def normalize_text(value: str | None) -> str:
    """Türkçe finansal metin için güvenli normalizasyon.

    Uygulanan adımlar (sıra önemlidir):
      1. Sıfır genişlikli karakterleri sil — NFKC bunları TEMİZLEMEZ
      2. Unicode NFKC normalizasyonu — ayrık yazılmış Türkçe harfleri de birleştirir
         (ör. 'g' + birleşen kısa çizgi → 'ğ')
      3. Boşluk benzeri karakterleri (nbsp dahil) normal boşluğa çevir
      4. Tire benzeri karakterleri (en-dash, em-dash, eksi) düz tireye çevir
      5. Fazla boşlukları indir, kırp

    Türkçe karakterler korunur; ASCII'ye çevrilmez.

    Args:
        value: Normalize edilecek metin. None ise boş dize döner.

    Returns:
        Normalize edilmiş metin.
    """
    if not value:
        return ""

    # 1. Görünmez karakterler NFKC'den ÖNCE silinir; NFKC onları kaldırmaz.
    value = _ZERO_WIDTH_RE.sub("", value)

    # 2. Uyumluluk karakterlerini kanonik biçime getir (ör. tam genişlikli ％ → %).
    value = unicodedata.normalize("NFKC", value)

    # 3. NFKC bazı boşlukları dönüştürse de tümünü kapsamaz.
    value = _SPACE_RE.sub(" ", value)

    # 4. Tarih aralıklarının doğru ayrıştırılması buna bağlıdır.
    value = _DASH_RE.sub("-", value)

    return collapse_whitespace(value)


def strip_tags(value: str) -> str:
    """HTML etiketlerini kaba biçimde kaldırır.

    Yapısal HTML temizliği `app.processing.cleaner` modülünde selector bazlı
    yapılır; bu fonksiyon yalnızca metin içine sızmış etiketler için son çaredir.

    Args:
        value: Etiket içerebilen metin.

    Returns:
        Etiketleri kaldırılmış metin.
    """
    return _TAG_RE.sub(" ", value)


def strip_boilerplate(html_or_text: str | None) -> str:
    """Çerez/KVKK/footer gibi tekrarlayan blokları metinden ayıklar.

    Satır bazlı çalışır: bilinen kalıplardan biriyle eşleşen satır atılır.
    Kampanya koşulu içeren satırları yanlışlıkla silmemek için kalıplar
    dar tutulmuştur.

    Args:
        html_or_text: Ham HTML veya düz metin.

    Returns:
        Boilerplate satırları çıkarılmış, normalize edilmiş metin.
    """
    if not html_or_text:
        return ""

    text = html_or_text
    if "<" in text and ">" in text:
        text = strip_tags(text)

    text = normalize_text(text)

    kept: list[str] = []
    for line in text.split("\n"):
        if not line:
            continue
        if any(pattern.search(line) for pattern in _BOILERPLATE_PATTERNS):
            continue
        kept.append(line)

    return collapse_whitespace("\n".join(kept))
