"""Yapısal oran tablosu ayrıştırma testleri.

Fixture canlı Türkiye Finans sayfasından alınmıştır; değerler gerçektir ve
görünmez karakterler korunmuştur.
"""

from __future__ import annotations

from decimal import Decimal

from app.processing.rate_tables import parse_rate_tables

FIXTURE = "html/turkiye_finans/oran_tablolari.html"


class TestVaryantAyrimi:
    """⚠️ Varyant boyutu tablonun DIŞINDA, üstteki başlıkta yazılı."""

    def test_iki_tablo_ayri_varyant_olarak_okunur(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        tablolar = parse_rate_tables(read_fixture(FIXTURE))
        assert [t.variant_key for t in tablolar] == ["sigortali", "sigortasiz"]

    def test_ham_baslik_saklanir(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        tablolar = parse_rate_tables(read_fixture(FIXTURE))
        assert tablolar[0].variant_label
        assert "Sigortalı" in tablolar[0].variant_label

    def test_varyantlar_karismiyor(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        """Karışırsa "en düşük kâr payı" karşılaştırması yanlış çıkar."""
        sigortali, sigortasiz = parse_rate_tables(read_fixture(FIXTURE))
        assert sigortali.rows[0].profit_rate_pct == Decimal("4.20")
        assert sigortasiz.rows[0].profit_rate_pct == Decimal("6.10")


class TestGorunmezKarakterler:
    """⚠️ Başlıklarda kelimenin İÇİNDE zero-width space var."""

    def test_kolonlar_dogru_eslesir(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        """Ham dize karşılaştırması yapılsaydı tüm kolonlar boş kalırdı."""
        satir = parse_rate_tables(read_fixture(FIXTURE))[0].rows[0]
        assert satir.term_months == 3
        assert satir.profit_rate_pct == Decimal("4.20")
        assert satir.allocation_fee_pct == Decimal("0.50")
        assert satir.monthly_cost_pct == Decimal("5.77")
        assert satir.annual_cost_pct == Decimal("96.05")


class TestDegerAyristirma:
    """Türkçe ondalık ayracı ve birimsiz vade."""

    def test_turkce_virgul_dogru_okunur(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        """ "4,20%" -> 4.20 (4 değil, 420 değil)."""
        satir = parse_rate_tables(read_fixture(FIXTURE))[0].rows[0]
        assert satir.profit_rate_pct == Decimal("4.20")

    def test_birimsiz_vade_okunur(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        """⚠️ Oran tablolarında vade birimsiz yazılıyor ("3", "36")."""
        vadeler = [r.term_months for r in parse_rate_tables(read_fixture(FIXTURE))[0].rows]
        assert vadeler == [3, 12, 36]

    def test_her_satirda_kanit_metni(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        for tablo in parse_rate_tables(read_fixture(FIXTURE)):
            for satir in tablo.rows:
                assert satir.evidence_text


class TestIlgisizTablolar:
    """Oran taşımayan tablolar atlanır."""

    def test_belge_tablosu_alinmaz(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        """Sayfada 3 tablo var; yalnızca 2'si oran tablosu."""
        assert len(parse_rate_tables(read_fixture(FIXTURE))) == 2

    def test_bos_girdi(self) -> None:
        assert parse_rate_tables(None) == []
        assert parse_rate_tables("") == []
        assert parse_rate_tables("<html><body><p>Tablo yok</p></body></html>") == []

    def test_baslik_satiri_olmayan_tablo_atlanir(self) -> None:
        assert parse_rate_tables("<table><tr><td>3</td></tr></table>") == []
