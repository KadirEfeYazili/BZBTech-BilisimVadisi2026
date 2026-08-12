"""Hesaplayıcı envanteri testleri (SPRINT 2 / KAPI 1).

Testler ağa çıkmaz: kaydedilmiş HTML üzerinde çalışır (§13).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.scrapers.calculator_inventory import (
    CalculatorForm,
    allowed_terms,
    amount_bounds,
    count_combinations,
    find_legal_notice,
    match_variant,
    parse_form_controls,
    suggest_sampling,
    variant_candidates,
)

ZIRAAT_KONUT = "html/ziraat_katilim/hesaplayici_konut.html"


@pytest.fixture
def ziraat_form(read_fixture) -> CalculatorForm:  # type: ignore[no-untyped-def]
    """Ziraat konut hesaplayıcısının envanteri."""
    return parse_form_controls(read_fixture(ZIRAAT_KONUT))


class TestFormEnvanteri:
    """`parse_form_controls` — form kontrollerinin çıkarılması."""

    def test_dropdown_secenekleri_tam_okunur(self, ziraat_form: CalculatorForm) -> None:
        """⚠️ KAPI 1 geçiş koşulu: Ziraat'in 16 seçeneği tam liste olmalı."""
        etiketler = [s["label"] for s in ziraat_form.input_fields["finansmanTipi"]["options"]]
        assert len(etiketler) == 16
        assert etiketler[0] == "Sıfır Konut"
        assert etiketler[1] == "2. El Konut"

    def test_yer_tutucu_secenek_sayilmaz(self, ziraat_form: CalculatorForm) -> None:
        """`value=""` olan "Seçiniz", varyant ve kombinasyon sayısını şişirirdi."""
        etiketler = [s["label"] for s in ziraat_form.input_fields["finansmanTipi"]["options"]]
        assert "Seçiniz" not in etiketler

    def test_value_niteligi_yoksa_etiket_deger_olur(self) -> None:
        """Bazı formlar `<option>` değerini yazmaz; etiket gerçek seçenektir."""
        form = parse_form_controls(
            "<select name='tip'><option>Sıfır Konut</option>"
            "<option>2. El Konut</option></select>"
        )
        secenekler = form.input_fields["tip"]["options"]
        assert [s["value"] for s in secenekler] == ["Sıfır Konut", "2. El Konut"]

    def test_secenek_degeri_korunur(self, ziraat_form: CalculatorForm) -> None:
        """`<option value>` sorgu şablonunda kullanılacak; etiketle karıştırılmaz."""
        secenekler = ziraat_form.input_fields["finansmanTipi"]["options"]
        sifir_konut = next(s for s in secenekler if s["label"] == "Sıfır Konut")
        assert sifir_konut["value"] == "1"

    def test_slider_sinirlari_okunur(self, ziraat_form: CalculatorForm) -> None:
        """HTML attribute en güvenilir limit kaynağıdır (`limits_source='html_attr'`)."""
        tutar = ziraat_form.input_fields["tutar"]
        assert tutar["type"] == "range"
        assert tutar["min"] == 50000
        assert tutar["max"] == 5000000
        assert tutar["step"] == 1000

    def test_radyo_grubu_tek_alanda_toplanir(self, ziraat_form: CalculatorForm) -> None:
        sigorta = ziraat_form.input_fields["sigortaDurumu"]
        assert sigorta["type"] == "radio"
        assert {s["label"] for s in sigorta["options"]} == {"Sigortalı", "Sigortasız"}

    def test_gizli_ve_gonder_kontrolleri_atlanir(self, ziraat_form: CalculatorForm) -> None:
        """CSRF token ve gönder düğmesi envanterde yer tutmaz."""
        assert "__RequestVerificationToken" not in ziraat_form.input_fields

    def test_bos_html_bos_envanter_verir(self) -> None:
        form = parse_form_controls("<html><body><p>Hesaplayıcı yok</p></body></html>")
        assert form.input_fields == {}


class TestYasalUyari:
    """`find_legal_notice` — bağlayıcılık kaydı."""

    def test_uyari_birebir_cikarilir(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        uyari = find_legal_notice(read_fixture(ZIRAAT_KONUT))
        assert uyari is not None
        assert "bilgi amaçlıdır" in uyari
        assert "bağlayıcı" in uyari

    def test_uyari_yoksa_none(self) -> None:
        assert find_legal_notice("<html><body><p>Konut finansmanı</p></body></html>") is None


class TestVaryantEslemesi:
    """`match_variant` — etiket → kanonik anahtar."""

    @pytest.mark.parametrize(
        ("etiket", "beklenen_boyut", "beklenen_anahtar"),
        [
            ("Sıfır Konut", "konut_durumu", "sifir_konut"),
            ("2. El Konut", "konut_durumu", "ikinci_el_konut"),
            ("Kentsel Dönüşüm Finansmanı", "konut_durumu", "kentsel_donusum"),
            ("TOKİ Konut Finansmanı", "konut_durumu", "toki"),
            ("Arsa Finansmanı", "konut_durumu", "arsa"),
            ("İş Yeri Finansmanı", "konut_durumu", "isyeri"),
            ("Sıfır Km Araç", "arac_durumu", "sifir_arac"),
            ("2. El Araç Finansmanı", "arac_durumu", "ikinci_el_arac"),
            ("Elektrikli Araç Finansmanı", "arac_durumu", "elektrikli_arac"),
            ("Sigortalı İhtiyaç Finansmanı", "sigorta", "sigortali"),
            ("Sigortasız İhtiyaç Finansmanı", "sigorta", "sigortasiz"),
            ("Karz-ı Hasen Finansmanı", "ozel", "karz_i_hasen"),
            ("Çevre Dostu Konut Finansmanı", "ozel", "cevre_dostu"),
        ],
    )
    def test_bilinen_etiketler_eslenir(
        self, etiket: str, beklenen_boyut: str, beklenen_anahtar: str
    ) -> None:
        boyut, anahtar = match_variant(etiket)
        assert (boyut, anahtar) == (beklenen_boyut, beklenen_anahtar)

    def test_turkce_karakter_ve_buyuk_harf_onemsiz(self) -> None:
        """"SIFIR KONUT", "sıfır konut" ve "Sıfır Konut" aynı anahtara gider."""
        sonuclar = {match_variant(y) for y in ("SIFIR KONUT", "sıfır konut", "Sıfır Konut")}
        assert sonuclar == {("konut_durumu", "sifir_konut")}

    def test_ozgul_kalip_genel_kaliba_baskin(self) -> None:
        """"2. El Konut" hem 'konut' hem '2. el' içerir; birleşik kalıp kazanmalı."""
        assert match_variant("2. El Konut") == ("konut_durumu", "ikinci_el_konut")
        assert match_variant("Sıfırsız 2. El Araç") == ("arac_durumu", "ikinci_el_arac")

    def test_eslesmeyen_etiket_uydurulmaz(self) -> None:
        """⚠️ Yanlış eşleme, sigortalı oranı sigortasızla kıyaslamaya yol açar."""
        assert match_variant("Gayrimenkul Yatırım Paketi") == (None, None)
        assert match_variant("") == (None, None)

    def test_kanonik_anahtarin_kendisi_de_eslenir(self) -> None:
        """API'den `value` olarak kanonik anahtar gelebilir."""
        assert match_variant("sifir_arac") == ("arac_durumu", "sifir_arac")


class TestVaryantAdaylari:
    """`variant_candidates` — dropdown → ürün varyantı."""

    def test_varyant_alani_en_kalabalik_metinli_select(
        self, ziraat_form: CalculatorForm
    ) -> None:
        """Vade seçicisi (12, 24, 36) varyant değildir; finansman tipi varyanttır."""
        assert ziraat_form.variant_field_name == "finansmanTipi"

    def test_onalti_aday_uretilir(self, ziraat_form: CalculatorForm) -> None:
        adaylar = variant_candidates(ziraat_form)
        assert len(adaylar) == 16

    def test_ham_etiket_birebir_tasinir(self, ziraat_form: CalculatorForm) -> None:
        adaylar = variant_candidates(ziraat_form)
        etiketler = [a.label for a in adaylar]
        assert "Kentsel Dönüşüm Finansmanı" in etiketler
        assert "Karz-ı Hasen Finansmanı" in etiketler

    def test_eslenmeyenler_isaretlenir(self, ziraat_form: CalculatorForm) -> None:
        """Eşlenemeyen adaylar `variant_mapping.md`'ye "eşlenmedi" olarak yazılacak."""
        adaylar = variant_candidates(ziraat_form)
        eslenmeyen = [a.label for a in adaylar if not a.is_mapped]
        assert "Gayrimenkul Yatırım Paketi" in eslenmeyen
        # Çoğunluk eşlenmeli; aksi hâlde kalıp tablosu yetersiz demektir.
        assert len(eslenmeyen) <= 2

    def test_varyant_alani_yoksa_bos_liste(self) -> None:
        assert variant_candidates(CalculatorForm()) == []


class TestLimitVeVade:
    """`amount_bounds` ve `allowed_terms`."""

    def test_tutar_sinirlari_decimal_doner(self, ziraat_form: CalculatorForm) -> None:
        """Para alanlarında float kullanılmaz."""
        en_az, en_cok = amount_bounds(ziraat_form.input_fields)
        assert en_az == Decimal("50000")
        assert en_cok == Decimal("5000000")
        assert isinstance(en_az, Decimal)

    def test_izinli_vadeler_cikarilir(self, ziraat_form: CalculatorForm) -> None:
        """Aralık yetmez: banka yalnızca bu vadeleri sunuyor."""
        assert allowed_terms(ziraat_form.input_fields) == [12, 24, 36, 48, 60]

    def test_alan_yoksa_none(self) -> None:
        assert amount_bounds({}) == (None, None)
        assert allowed_terms({}) is None


class TestKombinasyonVeOrnekleme:
    """`count_combinations` ve `suggest_sampling`."""

    def test_ziraat_kombinasyonu(self, ziraat_form: CalculatorForm) -> None:
        """16 varyant × 4 tutar noktası × 5 vade × 2 sigorta = 640."""
        assert count_combinations(ziraat_form.input_fields) == 16 * 4 * 5 * 2

    def test_bos_form_sifir(self) -> None:
        assert count_combinations({}) == 0

    @pytest.mark.parametrize(
        ("kombinasyon", "beklenen"),
        [
            (0, "skip"),
            (10, "full"),
            (60, "full"),
            (61, "grid"),
            (2_000, "grid"),
            (2_001, "pilot_only"),
            (100_000, "pilot_only"),
        ],
    )
    def test_ornekleme_karari_sayiya_gore(self, kombinasyon: int, beklenen: str) -> None:
        assert suggest_sampling(kombinasyon, "api") == beklenen

    @pytest.mark.parametrize("mekanizma", ["unknown", "none"])
    def test_mekanizma_cozulemezse_atlanir(self, mekanizma: str) -> None:
        """Playwright yoksa ya da mekanizma anlaşılmadıysa sorgulama yapılmaz."""
        assert suggest_sampling(10, mekanizma) == "skip"

    def test_ziraat_izgara_ornekler(self, ziraat_form: CalculatorForm) -> None:
        """640 kombinasyon tam tarama için çok, pilot için gereksiz dar."""
        toplam = count_combinations(ziraat_form.input_fields)
        assert suggest_sampling(toplam, "api") == "grid"
