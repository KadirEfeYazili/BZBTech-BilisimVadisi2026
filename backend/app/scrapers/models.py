"""Scraper katmanının veri taşıyıcıları.

Bu dataclass'lar ORM modellerinden BAĞIMSIZDIR: scraper'lar veritabanı
nesneleri değil, saf veri üretir. Kalıcılık `BaseScraper.run()` içinde tek
noktadan yapılır; böylece ayrıştırma mantığı veritabanı olmadan test edilebilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class DiscoveredUrl:
    """Keşif aşamasında bulunan bir adres ve o adres hakkında bilinenler.

    `*_hint` alanları keşif bağlamından gelir: örneğin Emlak Katılım'da
    /tr/bireysel/kampanyalar listesinden çıkan her adres bireysel segmenttedir.
    Bu bilgi detay sayfasında bulunmadığı için keşifte taşınır.
    """

    url: str
    doc_type: str  # campaign | product | listing | rate_table
    category_hint: str | None = None
    segment_hint: str | None = None  # bireysel | kurumsal | kobi | ticari | tarim
    discovery_method: str = "listing"


@dataclass
class RawCampaign:
    """Detay sayfasından çıkarılmış, henüz veritabanına yazılmamış kampanya."""

    external_slug: str
    title: str
    source_url: str
    description: str | None = None
    conditions_text: str | None = None
    exclusions_text: str | None = None
    category: str | None = None
    segment: str | None = None
    target_customer: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    date_precision: str = "unknown"
    participation_method: str | None = None
    participation_channel: str | None = None
    sms_keyword: str | None = None
    sms_number: str | None = None
    coupon_code: str | None = None
    is_archived: bool = False


@dataclass
class FetchResult:
    """Tek bir HTTP çekiminin sonucu.

    Başarısız çekimler de döndürülür (istisna fırlatılmaz): tek bir URL'in
    hatası tüm çalıştırmayı durdurmamalıdır (§12). Hata bilgisi `error`
    alanında taşınır ve `source_documents` kaydına yazılır.
    """

    url: str
    final_url: str | None = None
    status_code: int | None = None
    html: str | None = None
    content_type: str | None = None
    raw_html_path: str | None = None
    raw_html_sha256: str | None = None
    robots_allowed: bool = True
    is_soft_404: bool = False
    error: str | None = None

    @property
    def is_success(self) -> bool:
        """İçerik ayrıştırmaya uygun mu?"""
        return (
            self.robots_allowed
            and not self.is_soft_404
            and self.error is None
            and self.status_code is not None
            and 200 <= self.status_code < 300
            and bool(self.html)
        )


@dataclass
class ScrapeRunResult:
    """Bir kazıma çalıştırmasının özeti."""

    bank_code: str
    status: str = "running"
    run_id: int | None = None
    urls_discovered: int = 0
    urls_fetched: int = 0
    campaigns_new: int = 0
    campaigns_updated: int = 0
    errors_count: int = 0
    errors: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Hata kaydeder; çalıştırma durmaz, sayaç artar."""
        self.errors_count += 1
        # Log dosyasının şişmemesi için ilk 50 hata metni saklanır.
        if len(self.errors) < 50:
            self.errors.append(message)
