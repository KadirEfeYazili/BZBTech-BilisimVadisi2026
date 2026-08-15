"""Adil Katılım scraper'ı — KAMPANYA ÜRETMEZ, GERÇEĞİ BELGELER.

Bu bankanın kamuya açık kampanya sayfası YOK. Yine de sistemde bulunur ve
her çalıştırmada `scrape_runs`'a kayıt düşer: şartname 5.1 "faaliyet gösteren
kuruluşların tümü" diyor ve "veri yok" bilgisi de başlı başına bir bulgudur.
Gizlenmez, gerekçesiyle birlikte kayıt altına alınır.

⚠️ SOFT-404 CATCH-ALL — canlı ölçüm (14 Ağustos 2026):

    /                     -> HTTP 200, 895.617 bayt
    /olmayan-sayfa-xyz123 -> HTTP 200, 895.617 bayt, İÇERİK ANA SAYFAYLA AYNI
    /kampanyalar          -> HTTP 200, 895.617 bayt, İÇERİK ANA SAYFAYLA AYNI
    /sitemap.xml          -> HTTP 200, 895.617 bayt, İÇERİK ANA SAYFAYLA AYNI

Site VAR OLMAYAN HER ADRES için ana sayfayı döndürüyor. Başlık her seferinde
"Anasayfa | Adil Katılım"; gövdede hiçbir hata ifadesi yok. Metin desenine
bakan soft-404 sezgisi bu bankada ÇALIŞMAZ — ölçüldü, `is_soft_404` bayrağı
`False` kalıyor.

Tek ayırt edici işaret İÇERİĞİN ANA SAYFAYLA BİREBİR AYNI OLMASI. Bu yüzden
keşfin ilk adımı ana sayfayı çekip `content_fingerprint()` özetini hesaplamak
ve bunu `Fetcher`'a bildirmektir. Ondan sonra her yanıt bu özetle
karşılaştırılır; eşleşen sayfa "yok" sayılır ve kampanya kaydı OLUŞTURULMAZ.

Bu adım atlanırsa 9 adresin dokuzu da geçerli kampanya sanılır ve veri
setine dokuz çöp kayıt girer — hata vermeden.

⚠️ CRAWLER KURULMAZ. Her adres ana sayfayı döndürdüğü için bağlantı takibi
sonsuz döngüye girer. Sabit bir adres listesi kullanılır.

`robots.txt` boş; yine de `Fetcher` denetimi devrededir.
"""

from __future__ import annotations

from typing import Final

from app.logging_config import get_logger
from app.scrapers.base import BaseScraper
from app.scrapers.models import DiscoveredUrl, RawCampaign
from app.scrapers.soft404 import content_fingerprint

logger = get_logger(__name__)

BASE_URL: Final[str] = "https://www.adilkatilim.com.tr"

# Denetlenecek sabit adres listesi. Kampanya bulunursa diye bakılır; hiçbiri
# gerçek sayfa döndürmüyor, hepsi ana sayfaya düşüyor. Liste, "bakıldı ve
# yoktu" bilgisini kanıtlamak için tutulur — her adres `source_documents`'a
# yazılır ve ham HTML arşivlenir.
CANDIDATE_PATHS: Final[tuple[str, ...]] = (
    "/kampanyalar",
    "/kampanya",
    "/bireysel/kampanyalar",
    "/kurumsal/kampanyalar",
    "/duyurular",
    "/firsatlar",
    "/bireysel",
    "/kurumsal",
    "/hakkimizda",
)


class AdilKatilimScraper(BaseScraper):
    """Adil Katılım scraper'ı: kampanya aramaz, yokluğunu belgeler."""

    bank_code = "adil_katilim"
    version = "1.0.0"

    def discover(self) -> list[DiscoveredUrl]:
        """Ana sayfa parmak izini öğrenir, sonra aday adresleri döndürür.

        Ana sayfa ÖNCE çekilir: içerik özeti `Fetcher`'a bildirilmeden
        yapılan hiçbir denetim bu bankada çalışmaz.

        Returns:
            Denetlenecek adresler. Hepsinin soft-404'e düşmesi beklenir.
        """
        ana_sayfa = self.fetcher.fetch(f"{BASE_URL}/")
        parmak_izi = content_fingerprint(ana_sayfa.html)

        if parmak_izi:
            self.fetcher.add_soft_404_hash(parmak_izi)
            logger.info(
                "ana_sayfa_parmak_izi_kaydedildi",
                banka=self.bank_code,
                ozet=parmak_izi[:16],
            )
        else:
            # Parmak izi alınamazsa denetim yapılamaz; çöp kayıt riskine
            # karşı hiç aday döndürülmez.
            logger.warning(
                "ana_sayfa_alinamadi_kesif_durduruldu",
                banka=self.bank_code,
                durum=ana_sayfa.status_code,
                hata=ana_sayfa.error,
            )
            return []

        return [
            DiscoveredUrl(
                url=f"{BASE_URL}{yol}",
                doc_type="campaign",
                segment_hint="bireysel",
                discovery_method="listing",
            )
            for yol in CANDIDATE_PATHS
        ]

    def parse_detail(self, html: str, url: str, hint: DiscoveredUrl) -> RawCampaign | None:
        """Kampanya kaydı ÜRETMEZ.

        Buraya yalnızca soft-404 denetiminden geçmiş bir sayfa gelirse
        ulaşılır — yani beklenmedik biçimde gerçek bir sayfa bulunmuşsa.
        O durumda bile kayıt oluşturulmaz: bankanın kampanya yayımlamadığı
        tespiti elle doğrulanmadan veri setine kayıt girmemelidir.

        Args:
            html: Sayfanın HTML'i.
            url: Sayfanın adresi.
            hint: Keşiften gelen bağlam.

        Returns:
            Daima None.
        """
        logger.info(
            "beklenmedik_gercek_sayfa",
            banka=self.bank_code,
            url=url,
            not_="Kampanya kaydı oluşturulmadı; sayfa elle incelenmeli.",
        )
        return None
