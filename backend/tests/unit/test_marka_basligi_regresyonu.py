"""Marka başlığı tuzağı — canlı çekimde ortaya çıkan hatanın regresyon testleri.

ÖLÇÜM (14 Ağustos 2026, Ziraat Katılım canlı çekimi):

    213 arşiv dosyasının 213'ünde başlık "Ziraat Katılım Bankası" çıktı.
    2 dosya gerçek "sayfa yok" yanıtıydı; soft-404 sezgisi hiçbirini yakalamadı.

Tek kök neden: detay sayfalarının tepesinde logo metni de `<h1>` olarak
işaretlenmiş. Başlık zinciri ilk `<h1>`'i aldığı için hem kampanya adı hem de
"sayfa yok" bilgisi görünmez oldu.

Hatanın sinsiliği: hiçbir istisna fırlamadı, çalıştırma `success` ile kapandı,
209 kayıt yazıldı. Veri kirliliği yalnızca arayüze bakınca fark edildi.

Bu testler iki düzeltmeyi kilitler:
  1. `extract_title(..., ignore_headings=...)` — marka başlığı atlanır
  2. `is_soft_404` — ham `<title>` etiketine de bakar
"""

from __future__ import annotations

import pytest

from app.processing.cleaner import extract_title
from app.scrapers.banks.ziraat_katilim import BRAND_HEADINGS
from app.scrapers.soft404 import is_soft_404

MARKA_H1 = "html/ziraat_katilim/kampanya_marka_h1.html"
BULUNAMADI = "html/ziraat_katilim/sayfa_bulunamadi.html"


class TestMarkaBasligiAtlanir:
    """`extract_title(ignore_headings=...)`."""

    def test_yok_saymadan_marka_basligi_doner(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        """Hatanın kendisi: varsayılan davranış logo metnini alıyor."""
        assert extract_title(read_fixture(MARKA_H1)) == "Ziraat Katılım Bankası"

    def test_yok_sayilinca_gercek_kampanya_adi_doner(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        baslik = extract_title(read_fixture(MARKA_H1), ignore_headings=BRAND_HEADINGS)
        assert baslik == "Sosyopix'te %20 İndirim"

    def test_buyuk_kucuk_harf_ve_turkce_karakter_onemsiz(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        """ "ZIRAAT KATILIM BANKASI" yazımı da elenmeli."""
        baslik = extract_title(read_fixture(MARKA_H1), ignore_headings=("ZIRAAT KATILIM BANKASI",))
        assert baslik == "Sosyopix'te %20 İndirim"

    def test_bos_liste_davranisi_degistirmez(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        """Mevcut çağıranlar (Emlak, Hayat) etkilenmemeli."""
        assert extract_title(read_fixture(MARKA_H1), ignore_headings=()) == extract_title(
            read_fixture(MARKA_H1)
        )

    def test_tum_basliklar_yok_sayilirsa_zincir_devam_eder(self) -> None:
        """Marka dışında `<h1>` yoksa `og:title`'a düşülür."""
        html = (
            "<html><head><meta property='og:title' content='Yedek Başlık'></head>"
            "<body><h1>Ziraat Katılım Bankası</h1></body></html>"
        )
        assert extract_title(html, ignore_headings=BRAND_HEADINGS) == "Yedek Başlık"


class TestSoftNotFoundHamBaslik:
    """`is_soft_404` ham `<title>` etiketine de bakar."""

    def test_gorunen_baslik_marka_olsa_da_yakalanir(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        """⚠️ Düzeltmeden önce bu sayfa geçerli kampanya sanılıyordu."""
        assert is_soft_404(read_fixture(BULUNAMADI), "https://ornek.com.tr/k")

    def test_gercek_kampanya_yanlis_pozitif_uretmez(self, read_fixture) -> None:  # type: ignore[no-untyped-def]
        assert not is_soft_404(read_fixture(MARKA_H1), "https://ornek.com.tr/k")

    @pytest.mark.parametrize(
        "baslik",
        ["Sayfa bulunamadı | Ziraat Katılım", "404 | Vakıf Katılım", "Page Not Found"],
    )
    def test_title_etiketindeki_desenler_yakalanir(self, baslik: str) -> None:
        html = f"<html><head><title>{baslik}</title></head><body><h1>Marka</h1></body></html>"
        assert is_soft_404(html, "https://ornek.com.tr/k")

    def test_title_etiketi_yoksa_cokmez(self) -> None:
        html = "<html><body><h1>Kampanya Adı</h1><p>Uzun ve geçerli içerik.</p></body></html>"
        assert not is_soft_404(html, "https://ornek.com.tr/k")
