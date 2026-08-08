"""robots.txt denetimi — etik kazımanın zorunlu adımı.

Analizde doğrulandı:
  - Türkiye Finans `Disallow: /*pdf$` ve bir kampanya sayfasını yasaklıyor
  - Albaraka `Disallow: /*slug` ve `/tr/ticari-ve-kurumsal*` yasaklıyor
  - Emlak Katılım tamamen açık (`Allow: /`)

Yasaklı adreslere İSTEK YAPILMAZ. Kayıt `source_documents` tablosuna
`robots_allowed=False` ile yazılır; böylece verinin neden eksik olduğu
sonradan kanıtlanabilir.

ERİŞİLEMEYEN robots.txt DAVRANIŞI (RFC 9309 §2.3.1):
  - 4xx (dosya yok)          -> tüm adreslere izin verilir
  - 5xx / ağ hatası          -> geçici erişilemezlik, TEMKİNLİ davranılır ve
                                istek yapılmaz
Bu ayrım bilinçlidir: sunucu geçici hata verirken sınırsız istek göndermek
hem etik değildir hem de sunucuyu daha çok yorar.
"""

from __future__ import annotations

from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

from protego import Protego

from app.logging_config import get_logger

logger = get_logger(__name__)


class RobotsFetcher(Protocol):
    """robots.txt indirmek için gereken en küçük arayüz.

    Testlerde gerçek ağa çıkmadan sahte içerik verebilmek için soyutlanmıştır.
    """

    def __call__(self, robots_url: str) -> tuple[int | None, str | None]:
        """robots.txt içeriğini indirir.

        Returns:
            (http_durum_kodu, içerik). Ağ hatasında (None, None).
        """
        ...


def robots_url_for(url: str) -> str:
    """Verilen adresin ait olduğu host için robots.txt adresini üretir."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))


class RobotsCache:
    """Host başına robots.txt indirip bellekte tutan denetleyici.

    Aynı host için robots.txt yalnızca BİR KEZ indirilir.
    """

    def __init__(self, fetcher: RobotsFetcher, user_agent: str) -> None:
        """
        Args:
            fetcher: robots.txt indiren çağrılabilir nesne.
            user_agent: Kurallara karşı denetlenecek istemci kimliği.
        """
        self._fetcher = fetcher
        self._user_agent = user_agent
        # host -> (parser, erişilebilir_mi)
        self._cache: dict[str, tuple[Protego | None, bool]] = {}

    def _load(self, url: str) -> tuple[Protego | None, bool]:
        """Host için robots.txt yükler (önbellekten veya ağdan)."""
        host = urlsplit(url).netloc.lower()
        if host in self._cache:
            return self._cache[host]

        robots_address = robots_url_for(url)
        try:
            status, content = self._fetcher(robots_address)
        except Exception as exc:  # ağ hatası
            logger.warning("robots_indirilemedi", host=host, hata=str(exc))
            self._cache[host] = (None, False)
            return self._cache[host]

        if status is None or status >= 500:
            # Geçici sunucu hatası: temkinli davran.
            logger.warning("robots_gecici_hata", host=host, durum=status)
            self._cache[host] = (None, False)
        elif status >= 400 or not content:
            # robots.txt yok: her şeye izin var.
            logger.info("robots_yok_izin_verildi", host=host, durum=status)
            self._cache[host] = (None, True)
        else:
            self._cache[host] = (Protego.parse(content), True)

        return self._cache[host]

    def is_allowed(self, url: str) -> bool:
        """Adrese istek yapılmasına robots.txt izin veriyor mu?

        Args:
            url: Denetlenecek adres.

        Returns:
            İzin varsa True.
        """
        parser, reachable = self._load(url)
        if parser is None:
            return reachable
        allowed: bool = parser.can_fetch(url, self._user_agent)
        if not allowed:
            logger.info("robots_engelledi", url=url)
        return allowed

    def crawl_delay(self, url: str) -> float | None:
        """robots.txt'te belirtilen bekleme süresini saniye olarak döndürür.

        Sitenin talep ettiği süre yapılandırmadaki süreden uzunsa ona uyulur.

        Args:
            url: İlgili adres.

        Returns:
            Saniye cinsinden bekleme süresi veya belirtilmemişse None.
        """
        parser, _ = self._load(url)
        if parser is None:
            return None
        delay = parser.crawl_delay(self._user_agent)
        return float(delay) if delay is not None else None
