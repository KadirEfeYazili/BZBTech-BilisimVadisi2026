"""SPRINT 2 

Buradaki kısıtlar "yanlış veriyi hata vererek reddet" içindir. Sessizce kabul
edilen bozuk bir varyant etiketi ya da kaynağı belirtilmemiş bir oran,
karşılaştırma aşamasında yanlış sonuç üretir ve o noktada nereden geldiği
bulunamaz.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Bank,
    CalculatorInventory,
    CalculatorProbe,
    Campaign,
    CampaignCategory,
    Product,
    ProductRate,
)


@pytest.fixture
def banka(db_session: Session) -> Bank:
    """Testler için tek bir banka kaydı."""
    bank = Bank(code="ornek_katilim", name="Örnek Katılım", website="https://ornek.com.tr")
    db_session.add(bank)
    db_session.flush()
    return bank


@pytest.fixture
def urun(db_session: Session, banka: Bank) -> Product:
    """Varyantsız ana ürün."""
    product = Product(bank_id=banka.id, name="Konut Finansmanı", product_type="konut_finansmani")
    db_session.add(product)
    db_session.flush()
    return product


@pytest.fixture
def kampanya(db_session: Session, banka: Bank) -> Campaign:
    """Taksonomi testleri için kampanya."""
    campaign = Campaign(
        bank_id=banka.id,
        external_slug="akaryakit-kampanyasi",
        title="Akaryakıt Kampanyası",
        source_url="https://ornek.com.tr/kampanya/akaryakit",
    )
    db_session.add(campaign)
    db_session.flush()
    return campaign


class TestUrunVaryanti:
    """`products` varyant boyutu."""

    def test_varyant_ana_urune_baglanir(
        self, db_session: Session, banka: Bank, urun: Product
    ) -> None:
        """Her varyant kendi satırıdır ve `parent_product_id` ile bağlanır."""
        for anahtar, etiket in (("sifir_konut", "Sıfır Konut"), ("ikinci_el_konut", "2. El Konut")):
            db_session.add(
                Product(
                    bank_id=banka.id,
                    parent_product_id=urun.id,
                    name=f"Konut Finansmanı — {etiket}",
                    product_type="konut_finansmani",
                    variant_key=anahtar,
                    variant_label=etiket,
                    variant_dimension="konut_durumu",
                    variant_source="dropdown_option",
                )
            )
        db_session.flush()
        db_session.refresh(urun)

        assert len(urun.variants) == 2
        assert {v.variant_key for v in urun.variants} == {"sifir_konut", "ikinci_el_konut"}
        assert all(v.parent is urun for v in urun.variants)

    def test_ham_etiket_birebir_saklanir(
        self, db_session: Session, banka: Bank, urun: Product
    ) -> None:
        """`variant_label` kaynaktaki metindir; kanonikleştirme `variant_key`'de yapılır."""
        ham = "Sıfır Km Araç (0 KM)"
        db_session.add(
            Product(
                bank_id=banka.id,
                parent_product_id=urun.id,
                name="Taşıt Finansmanı",
                variant_key="sifir_arac",
                variant_label=ham,
                variant_dimension="arac_durumu",
                variant_source="dropdown_option",
            )
        )
        db_session.flush()

        kayit = db_session.query(Product).filter_by(variant_key="sifir_arac").one()
        assert kayit.variant_label == ham

    def test_gecersiz_boyut_reddedilir(self, db_session: Session, banka: Bank) -> None:
        db_session.add(Product(bank_id=banka.id, name="X", variant_dimension="uydurma_boyut"))
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_gecersiz_limit_kaynagi_reddedilir(self, db_session: Session, banka: Bank) -> None:
        db_session.add(Product(bank_id=banka.id, name="X", limits_source="tahmin"))
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_ters_tutar_araligi_reddedilir(self, db_session: Session, banka: Bank) -> None:
        """`5.000` ile `50.000`in karışması bu kısıtta yakalanır."""
        db_session.add(
            Product(
                bank_id=banka.id,
                name="X",
                amount_min=Decimal("50000.00"),
                amount_max=Decimal("5000.00"),
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_ters_vade_araligi_reddedilir(self, db_session: Session, banka: Bank) -> None:
        db_session.add(Product(bank_id=banka.id, name="X", term_months_min=36, term_months_max=12))
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_varsayilanlar(self, db_session: Session, urun: Product) -> None:
        """Para birimi TRY, bağlayıcılık açık, hesaplayıcı kapalı başlar."""
        db_session.refresh(urun)
        assert urun.currency == "TRY"
        assert urun.is_binding is True
        assert urun.has_calculator is False

    def test_izinli_vadeler_liste_olarak_saklanir(self, db_session: Session, banka: Bank) -> None:
        """Aralık yetmez: bazı bankalar yalnızca belirli vadeleri sunuyor."""
        db_session.add(
            Product(bank_id=banka.id, name="İhtiyaç Finansmanı", allowed_terms=[3, 6, 12, 24, 36])
        )
        db_session.flush()
        db_session.expire_all()

        kayit = db_session.query(Product).filter_by(name="İhtiyaç Finansmanı").one()
        assert kayit.allowed_terms == [3, 6, 12, 24, 36]


class TestUrunOrani:
    """`product_rates` kaynak ve bant boyutu."""

    def test_guven_kaynaktan_turetilir(self, db_session: Session, urun: Product) -> None:
        """`rate_source` ile `confidence` elle ayrı yazılırsa birbirinden kopar."""
        oran = ProductRate(product_id=urun.id, term_months=12, rate_source="text")
        db_session.add(oran)
        db_session.flush()

        assert oran.confidence == Decimal("0.750")

    def test_acik_verilen_guven_korunur(self, db_session: Session, urun: Product) -> None:
        oran = ProductRate(
            product_id=urun.id, term_months=12, rate_source="text", confidence=Decimal("0.600")
        )
        db_session.add(oran)
        db_session.flush()

        assert oran.confidence == Decimal("0.600")

    def test_kaynaksiz_oran_varsayilanla_kaydedilir(
        self, db_session: Session, urun: Product
    ) -> None:
        """`rate_source` NOT NULL'dur; ORM varsayılanı `html_table`'dır."""
        oran = ProductRate(product_id=urun.id, term_months=12)
        db_session.add(oran)
        db_session.flush()

        assert oran.rate_source == "html_table"

    def test_gecersiz_kaynak_reddedilir(self, db_session: Session, urun: Product) -> None:
        db_session.add(ProductRate(product_id=urun.id, rate_source="kulaktan_dolma"))
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_bir_ustu_guven_reddedilir(self, db_session: Session, urun: Product) -> None:
        db_session.add(
            ProductRate(product_id=urun.id, rate_source="html_table", confidence=Decimal("1.500"))
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_ters_arac_yasi_araligi_reddedilir(self, db_session: Session, urun: Product) -> None:
        db_session.add(
            ProductRate(
                product_id=urun.id,
                rate_source="html_table",
                vehicle_age_min=10,
                vehicle_age_max=3,
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_enerji_sinifi_bandi_saklanir(self, db_session: Session, urun: Product) -> None:
        """Konut oranı enerji sınıfına göre değişir; ayrı satırlarda tutulur."""
        for sinif, oran_pct in (("A", Decimal("3.4900")), ("B", Decimal("3.7500"))):
            db_session.add(
                ProductRate(
                    product_id=urun.id,
                    term_months=120,
                    profit_rate_pct=oran_pct,
                    energy_class=sinif,
                    rate_source="html_table",
                    evidence_text=f"Enerji sınıfı {sinif}: %{oran_pct}",
                )
            )
        db_session.flush()
        db_session.refresh(urun)

        assert len(urun.rates) == 2
        assert {r.energy_class for r in urun.rates} == {"A", "B"}


class TestKampanyaTaksonomisi:
    """`campaign_categories` çok eksenli etiketleme."""

    def test_ayni_kampanya_birden_fazla_eksende_etiketlenir(
        self, db_session: Session, kampanya: Campaign
    ) -> None:
        for eksen, deger in (("product_type", "kart"), ("sector", "akaryakit")):
            db_session.add(
                CampaignCategory(campaign_id=kampanya.id, axis=eksen, value=deger, source="keyword")
            )
        db_session.flush()
        db_session.refresh(kampanya)

        assert {(c.axis, c.value) for c in kampanya.categories} == {
            ("product_type", "kart"),
            ("sector", "akaryakit"),
        }

    def test_ayni_eksende_birden_fazla_etiket_olabilir(
        self, db_session: Session, kampanya: Campaign
    ) -> None:
        """Bir kampanya hem markete hem akaryakıta ait olabilir."""
        for deger in ("market", "akaryakit"):
            db_session.add(
                CampaignCategory(
                    campaign_id=kampanya.id, axis="sector", value=deger, source="merchant"
                )
            )
        db_session.flush()

        assert db_session.query(CampaignCategory).count() == 2

    def test_ayni_etiket_iki_kez_yazilamaz(self, db_session: Session, kampanya: Campaign) -> None:
        """Sınıflandırıcı tekrar çalıştığında kayıt çoğalmamalı."""
        for _ in range(2):
            db_session.add(
                CampaignCategory(
                    campaign_id=kampanya.id, axis="sector", value="market", source="keyword"
                )
            )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_gecersiz_eksen_reddedilir(self, db_session: Session, kampanya: Campaign) -> None:
        db_session.add(
            CampaignCategory(campaign_id=kampanya.id, axis="renk", value="mavi", source="keyword")
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_gecersiz_kaynak_reddedilir(self, db_session: Session, kampanya: Campaign) -> None:
        db_session.add(
            CampaignCategory(
                campaign_id=kampanya.id, axis="sector", value="market", source="tahmin"
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_kampanya_silinince_etiketler_de_silinir(
        self, db_session: Session, kampanya: Campaign
    ) -> None:
        db_session.add(
            CampaignCategory(
                campaign_id=kampanya.id, axis="sector", value="market", source="keyword"
            )
        )
        db_session.flush()

        db_session.delete(kampanya)
        db_session.flush()

        assert db_session.query(CampaignCategory).count() == 0


class TestHesaplayiciEnvanteri:
    """`calculator_inventory` ve `calculator_probes`."""

    def test_envanter_girdi_alanlarini_saklar(self, db_session: Session, banka: Bank) -> None:
        """Dropdown seçenekleri ürün varyantlarının kaynağıdır."""
        alanlar = {
            "finansman_tipi": {
                "type": "select",
                "options": [
                    {"value": "1", "label": "Sıfır Konut"},
                    {"value": "2", "label": "2. El Konut"},
                ],
            },
            "tutar": {"type": "range", "min": 50000, "max": 5000000, "step": 1000},
        }
        db_session.add(
            CalculatorInventory(
                bank_id=banka.id,
                page_url="https://ornek.com.tr/hesaplama",
                input_fields=alanlar,
                variant_count=2,
                mechanism="js_client_side",
                sampling_decision="pilot_only",
            )
        )
        db_session.flush()
        db_session.expire_all()

        kayit = db_session.query(CalculatorInventory).one()
        assert kayit.input_fields["finansman_tipi"]["options"][0]["label"] == "Sıfır Konut"
        assert kayit.variant_count == 2
        assert kayit.feasible is False

    def test_gecersiz_mekanizma_reddedilir(self, db_session: Session, banka: Bank) -> None:
        db_session.add(
            CalculatorInventory(
                bank_id=banka.id, page_url="https://x", input_fields={}, mechanism="sihir"
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_ayni_sayfa_iki_kez_envanterlenemez(self, db_session: Session, banka: Bank) -> None:
        for _ in range(2):
            db_session.add(
                CalculatorInventory(
                    bank_id=banka.id,
                    page_url="https://ornek.com.tr/hesaplama",
                    input_fields={},
                    mechanism="api",
                )
            )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_sorgu_varsayilan_olarak_baglayici_degildir(
        self, db_session: Session, banka: Bank, urun: Product
    ) -> None:
        """Hesaplayıcı çıktısı bankanın taahhüdü değildir."""
        sorgu = CalculatorProbe(
            product_id=urun.id,
            bank_id=banka.id,
            probe_amount=Decimal("100000.00"),
            probe_term_months=12,
            method="api",
            probed_at=datetime.now(UTC),
        )
        db_session.add(sorgu)
        db_session.flush()

        assert sorgu.is_binding is False

    def test_katilim_terminolojisi_alan_adlarinda(self) -> None:
        """`total_profit_share` bulunur; konvansiyonel karşılığı BULUNMAZ."""
        kolonlar = set(CalculatorProbe.__table__.columns.keys())
        assert "total_profit_share" in kolonlar
        yasakli = {"total_interest", "interest_rate", "loan_amount", "deposit"}
        assert not (kolonlar & yasakli)

    def test_sifir_tutarli_sorgu_reddedilir(
        self, db_session: Session, banka: Bank, urun: Product
    ) -> None:
        db_session.add(
            CalculatorProbe(
                product_id=urun.id,
                bank_id=banka.id,
                probe_amount=Decimal("0.00"),
                probe_term_months=12,
                method="api",
                probed_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_gecersiz_yontem_reddedilir(
        self, db_session: Session, banka: Bank, urun: Product
    ) -> None:
        db_session.add(
            CalculatorProbe(
                product_id=urun.id,
                bank_id=banka.id,
                probe_amount=Decimal("1000.00"),
                probe_term_months=12,
                method="tahmin",
                probed_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
