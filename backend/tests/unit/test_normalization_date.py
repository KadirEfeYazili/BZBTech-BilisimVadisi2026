"""Türkçe tarih ayrıştırma testleri.

Şartnamedeki 7 zorunlu biçimin tamamı ve "tahmin yok" kuralı burada doğrulanır.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.core.normalization.date_tr import (
    TURKISH_MONTHS,
    parse_date_range_tr,
    parse_date_tr,
)


class TestZorunluBicimler:
    """Analizde doğrulanan 7 tarih biçimi."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            # 1. DD.MM.YYYY - DD.MM.YYYY
            (
                "Kampanya 01.01.2026 - 31.12.2026 tarihleri arasında geçerlidir.",
                (date(2026, 1, 1), date(2026, 12, 31), "exact"),
            ),
            # 2. Tek haneli gün
            ("6.08.2026 - 31.12.2026", (date(2026, 8, 6), date(2026, 12, 31), "exact")),
            # 3. Türkçe ay adı, iki yıl da yazılı
            (
                "6 Ağustos 2026 - 31 Aralık 2026",
                (date(2026, 8, 6), date(2026, 12, 31), "exact"),
            ),
            # 4. Gün aralığı, ay ve yıl ortak
            (
                "Kampanya 1-31 Ağustos 2026 tarihleri arasında geçerlidir.",
                (date(2026, 8, 1), date(2026, 8, 31), "exact"),
            ),
            # 5. Başlangıçta yıl yok -> çıkarım
            ("10 Temmuz - 7 Ağustos 2026", (date(2026, 7, 10), date(2026, 8, 7), "inferred")),
            # 6. Yalnızca bitiş
            ("Son Gün 31.12.2026", (None, date(2026, 12, 31), "partial")),
            # 7. Tire ayırıcı, yalnızca bitiş
            ("07-08-2026 Tarihinde Sona Ermiştir", (None, date(2026, 8, 7), "partial")),
        ],
    )
    def test_bicimler(self, text: str, expected: tuple[date | None, date | None, str]) -> None:
        assert parse_date_range_tr(text) == expected


class TestEkBicimler:
    def test_tarihine_kadar(self) -> None:
        assert parse_date_range_tr("31.12.2026 tarihine kadar geçerlidir") == (
            None,
            date(2026, 12, 31),
            "partial",
        )

    def test_itibaren_ve_kadar_birlikte(self) -> None:
        """Başlangıç ve bitiş ayrı ayrı işaretlenmişse ikisi de yakalanır."""
        assert parse_date_range_tr("01.01.2026 tarihinden itibaren 31.12.2026 tarihine kadar") == (
            date(2026, 1, 1),
            date(2026, 12, 31),
            "exact",
        )

    def test_saat_ifadesi_araligi_bozmaz(self) -> None:
        assert parse_date_range_tr("15 Haziran 2026 saat 00.01 - 15 Temmuz 2026 saat 23.59") == (
            date(2026, 6, 15),
            date(2026, 7, 15),
            "exact",
        )

    def test_ascii_ay_adlari(self) -> None:
        assert parse_date_range_tr("6 Agustos 2026 - 31 Aralik 2026") == (
            date(2026, 8, 6),
            date(2026, 12, 31),
            "exact",
        )

    def test_egik_cizgi_ayirici(self) -> None:
        assert parse_date_range_tr("01/01/2026 - 31/12/2026") == (
            date(2026, 1, 1),
            date(2026, 12, 31),
            "exact",
        )

    def test_yil_asan_aralikta_baslangic_yili_geri_alinir(self) -> None:
        """ "20 Aralık - 10 Ocak 2027" ifadesinde başlangıç bir önceki yıldadır."""
        assert parse_date_range_tr("20 Aralık - 10 Ocak 2027") == (
            date(2026, 12, 20),
            date(2027, 1, 10),
            "inferred",
        )


class TestTahminYok:
    """Belirsiz durumlarda tarih UYDURULMAZ."""

    def test_isaretsiz_tek_tarih_unknown_dondurur(self) -> None:
        """Gerçek senaryo: kampanya süresiyle ilgisi olmayan tarih.

        Emlak Katılım metninde geçen bu tarih kampanya bitişi DEĞİLDİR.
        """
        assert parse_date_range_tr(
            "Kullanılmayan puanlar 15 Ekim 2026 tarihinde geri alınacaktır."
        ) == (None, None, "unknown")

    @pytest.mark.parametrize("text", [None, "", "Kampanya devam ediyor", "Detaylar şubelerimizde"])
    def test_tarih_yoksa_unknown(self, text: str | None) -> None:
        assert parse_date_range_tr(text) == (None, None, "unknown")

    def test_gecersiz_tarih_kabul_edilmez(self) -> None:
        """31 Şubat diye bir tarih yoktur."""
        assert parse_date_range_tr("31.02.2026 - 31.12.2026") == (None, None, "unknown")


class TestParseDateTr:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("6 Ağustos 2026", date(2026, 8, 6)),
            ("01.01.2026", date(2026, 1, 1)),
            ("07-08-2026", date(2026, 8, 7)),
            ("1 Oca 2026", date(2026, 1, 1)),
        ],
    )
    def test_tekil_tarih(self, text: str, expected: date) -> None:
        assert parse_date_tr(text) == expected

    @pytest.mark.parametrize("text", [None, "", "tarih yok", "32.13.2026"])
    def test_tarih_yoksa_none(self, text: str | None) -> None:
        assert parse_date_tr(text) is None


class TestAyTablosu:
    def test_on_iki_ay_tanimli(self) -> None:
        assert len(TURKISH_MONTHS) == 12
        assert TURKISH_MONTHS["ağustos"] == 8
        assert TURKISH_MONTHS["aralık"] == 12

    @pytest.mark.parametrize(
        ("ay_adi", "ay_no"),
        list(TURKISH_MONTHS.items()),
    )
    def test_her_ay_ayristirilabilir(self, ay_adi: str, ay_no: int) -> None:
        assert parse_date_tr(f"15 {ay_adi} 2026") == date(2026, ay_no, 15)
