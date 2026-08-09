"""Seed verisinin testleri."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Bank, Campaign, GlossaryTerm
from app.db.seed import BANK_SEED, run_seed


class TestBankaSeed:
    def test_on_banka_yukleniyor(self, db_session: Session) -> None:
        run_seed(db_session)
        assert db_session.scalar(select(func.count()).select_from(Bank)) == 10
        assert len(BANK_SEED) == 10

    def test_kapsam_disi_banka_seedde_yok(self, db_session: Session) -> None:
        run_seed(db_session)
        kodlar = {b.code for b in db_session.scalars(select(Bank))}
        assert "iktisat_katilim" not in kodlar

    def test_kampanyasiz_banka_data_status_none(self, db_session: Session) -> None:
        run_seed(db_session)
        adil = db_session.scalar(select(Bank).where(Bank.code == "adil_katilim"))
        assert adil is not None
        assert adil.data_status == "none"
        assert adil.notes

    def test_tekrar_calistirmak_kayit_cogaltmaz(self, db_session: Session) -> None:
        run_seed(db_session)
        ikinci = run_seed(db_session)

        assert ikinci["banks_inserted"] == 0
        assert ikinci["glossary_inserted"] == 0
        assert db_session.scalar(select(func.count()).select_from(Bank)) == 10


class TestKapsamDisiBankaTemizligi:
    """Seed listesi tek doğruluk kaynağıdır; listeden çıkan banka silinir."""

    def test_listede_olmayan_banka_siliniyor(self, db_session: Session) -> None:
        run_seed(db_session)

        db_session.add(
            Bank(
                code="kapsam_disi_banka",
                name="Kapsam Dışı Banka",
                website="https://ornek.com.tr",
            )
        )
        db_session.flush()
        assert db_session.scalar(select(func.count()).select_from(Bank)) == 11

        ozet = run_seed(db_session)

        assert ozet["banks_removed"] == 1
        assert db_session.scalar(select(func.count()).select_from(Bank)) == 10

    def test_kampanyasi_olan_banka_silinmez(self, db_session: Session) -> None:
        """⚠️ Güvenlik kilidi: veri kaybını önler."""
        run_seed(db_session)

        banka = Bank(
            code="veri_tasiyan_banka",
            name="Veri Taşıyan Banka",
            website="https://ornek.com.tr",
        )
        db_session.add(banka)
        db_session.flush()
        db_session.add(
            Campaign(
                bank_id=banka.id,
                external_slug="ornek-kampanya",
                title="Örnek Kampanya",
                source_url="https://ornek.com.tr/kampanya",
            )
        )
        db_session.flush()

        ozet = run_seed(db_session)

        assert ozet["banks_removed"] == 0
        assert db_session.scalar(select(Bank).where(Bank.code == "veri_tasiyan_banka"))


class TestGlossarySeed:
    def test_sartnamedeki_bes_kavram_mevcut(self, db_session: Session) -> None:
        run_seed(db_session)
        terimler = {g.term for g in db_session.scalars(select(GlossaryTerm))}

        for kavram in (
            "Kâr Payı Oranı",
            "Finansman Maliyeti",
            "Katılım Fonu",
            "Masrafsız Finansman",
            "Avantajlı Finansman",
        ):
            assert kavram in terimler

    def test_yasakli_konvansiyonel_terimler_isaretli(self, db_session: Session) -> None:
        run_seed(db_session)
        yasakli = {
            g.term: g
            for g in db_session.scalars(
                select(GlossaryTerm).where(GlossaryTerm.is_forbidden_conventional.is_(True))
            )
        }

        assert "faiz" in yasakli
        assert "kredi" in yasakli
        assert "mevduat" in yasakli
        # Yasaklı kayıtta kullanılması gereken katılım karşılığı yazılıdır.
        assert yasakli["faiz"].conventional_equivalent == "kâr payı"
        assert yasakli["kredi"].conventional_equivalent == "finansman"
