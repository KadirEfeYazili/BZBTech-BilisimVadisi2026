"""Vade ve taksit ayrıştırma testleri."""

from __future__ import annotations

import pytest

from app.core.normalization.term import parse_installment_count, parse_term_months


class TestParseTermMonths:
    """Şartnamedeki vade ayrıştırma tablosu. Tüm değerler AY cinsinden."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("120 ay", (120, 120)),
            ("120 aya kadar", (None, 120)),
            ("36 aya varan vade", (None, 36)),
            ("10 yıl", (120, 120)),
            ("3-36 ay", (3, 36)),
            ("32 günden başlayan vadelerle", (1, None)),
            ("6 - 12 ay", (6, 12)),
            ("azami 60 ay", (None, 60)),
            ("en az 12 ay", (12, None)),
        ],
    )
    def test_vade_ayristirma(self, text: str, expected: tuple[int | None, int | None]) -> None:
        assert parse_term_months(text) == expected

    @pytest.mark.parametrize("text", [None, "", "kampanya", "hemen başvurun"])
    def test_vade_bulunamazsa_none(self, text: str | None) -> None:
        assert parse_term_months(text) == (None, None)

    def test_gun_donusumu_en_az_bir_ay(self) -> None:
        """Kısa gün vadeleri sıfır aya yuvarlanmaz."""
        assert parse_term_months("7 gün") == (1, 1)

    def test_yil_aya_cevrilir(self) -> None:
        assert parse_term_months("5 yıl") == (60, 60)

    def test_ascii_yazim_desteklenir(self) -> None:
        assert parse_term_months("10 yil") == (120, 120)


class TestParseInstallmentCount:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("6 taksit", 6),
            ("vade farksız 6 taksit", 6),
            ("4 aya varan taksit", 4),
            ("peşin fiyatına 12 taksit", 12),
            ("36 ay vade, 12 taksit", 12),
            ("taksit sayısı: 9", 9),
            ("9 aya varan taksit fırsatı", 9),
        ],
    )
    def test_taksit_sayisi(self, text: str, expected: int) -> None:
        assert parse_installment_count(text) == expected

    @pytest.mark.parametrize("text", [None, "", "kampanya", "120 ay vade"])
    def test_taksit_bulunamazsa_none(self, text: str | None) -> None:
        assert parse_installment_count(text) is None
