"""Metin normalizasyonu testleri.

En kritik senaryo: Türkiye Finans'ın oran tablosu başlıklarındaki görünmez
karakterler. Temizlenmezlerse kolon eşleştirmesi sessizce başarısız olur.
"""

from __future__ import annotations

import pytest

from app.core.normalization.text import (
    ascii_fold_tr,
    collapse_whitespace,
    lower_tr,
    normalize_text,
    strip_boilerplate,
    strip_tags,
)

ZWSP = chr(0x200B)  # zero width space
NBSP = chr(0x00A0)  # non-breaking space
BOM = chr(0xFEFF)  # byte order mark
SOFT_HYPHEN = chr(0x00AD)
EN_DASH = chr(0x2013)
EM_DASH = chr(0x2014)
MINUS_SIGN = chr(0x2212)


class TestGorunmezKarakterler:
    """Sıfır genişlikli ve boşluk benzeri karakterlerin temizlenmesi."""

    def test_zero_width_space_temizlenir(self) -> None:
        assert normalize_text(f"{ZWSP}Vade") == "Vade"

    def test_non_breaking_space_bosluga_cevrilir(self) -> None:
        assert normalize_text(f"Kâr{NBSP}Payı") == "Kâr Payı"

    def test_bom_temizlenir(self) -> None:
        assert normalize_text(f"{BOM}Kampanya") == "Kampanya"

    def test_soft_hyphen_temizlenir(self) -> None:
        assert normalize_text(f"fi{SOFT_HYPHEN}nansman") == "finansman"

    def test_turkiye_finans_tablo_basligi_senaryosu(self) -> None:
        """Gerçek veriden alınan bozuk başlık düzgün metne dönmeli."""
        bozuk = f"{ZWSP}Vade{NBSP}{ZWSP}Kâr{NBSP}Payı Oranı"
        assert normalize_text(bozuk) == "Vade Kâr Payı Oranı"


class TestTireNormalizasyonu:
    """Tarih aralıklarının ayrıştırılabilmesi tire birleştirmeye bağlıdır."""

    @pytest.mark.parametrize("dash", [EN_DASH, EM_DASH, MINUS_SIGN, chr(0x2011)])
    def test_tire_varyantlari_duz_tireye_cevrilir(self, dash: str) -> None:
        assert normalize_text(f"10 Temmuz {dash} 7 Ağustos") == "10 Temmuz - 7 Ağustos"


class TestTurkceKarakterKorunumu:
    """Türkçe karakterler ASCII'ye ÇEVRİLMEZ."""

    @pytest.mark.parametrize(
        "value",
        ["ığüşöçİĞÜŞÖÇ", "Kâr Payı Oranı", "Ağustos", "İstanbul Şubesi"],
    )
    def test_turkce_karakterler_korunur(self, value: str) -> None:
        assert normalize_text(value) == value


class TestBosluk:
    def test_fazla_bosluk_indirgenir(self) -> None:
        assert normalize_text("  çok    fazla   boşluk  ") == "çok fazla boşluk"

    def test_satir_yapisi_korunur(self) -> None:
        assert collapse_whitespace("bir\n\niki") == "bir\n\niki"

    def test_ucten_fazla_satir_sonu_indirgenir(self) -> None:
        assert collapse_whitespace("bir\n\n\n\niki") == "bir\n\niki"


class TestBosGirdiler:
    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_bos_girdi_bos_dize_dondurur(self, value: str | None) -> None:
        assert normalize_text(value) == ""


class TestLowerTr:
    def test_buyuk_i_dogru_kucultulur(self) -> None:
        """Python'un str.lower() metodu 'İ' için birleşen nokta bırakır."""
        combining_dot_above = chr(0x0307)
        assert lower_tr("İSTANBUL") == "istanbul"
        assert combining_dot_above not in lower_tr("İSTANBUL")
        # Karşılaştırma: standart lower() bu hatayı yapar.
        assert combining_dot_above in "İSTANBUL".lower()

    def test_noktasiz_i_dogru_kucultulur(self) -> None:
        assert lower_tr("IĞDIR") == "ığdır"


class TestAsciiFold:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [("Ağustos", "Agustos"), ("şubat", "subat"), ("Aralık", "Aralik")],
    )
    def test_ascii_katlama(self, value: str, expected: str) -> None:
        assert ascii_fold_tr(value) == expected


class TestBoilerplate:
    def test_cerez_satiri_atilir(self) -> None:
        metin = "Kampanya detayı.\nÇerez Politikası hakkında bilgi alın.\nKoşullar."
        sonuc = strip_boilerplate(metin)
        assert "Çerez" not in sonuc
        assert "Kampanya detayı." in sonuc
        assert "Koşullar." in sonuc

    def test_telif_satiri_atilir(self) -> None:
        assert "saklıdır" not in strip_boilerplate("İçerik\nTüm hakları saklıdır.")

    def test_kampanya_metni_korunur(self) -> None:
        metin = "5.000 TL ve üzeri harcamaya 250 TL değerinde hediye."
        assert strip_boilerplate(metin) == metin

    @pytest.mark.parametrize("value", [None, ""])
    def test_bos_girdi(self, value: str | None) -> None:
        assert strip_boilerplate(value) == ""


class TestStripTags:
    def test_etiketler_kaldirilir(self) -> None:
        assert collapse_whitespace(strip_tags("<p>Merhaba <b>dünya</b></p>")) == "Merhaba dünya"
