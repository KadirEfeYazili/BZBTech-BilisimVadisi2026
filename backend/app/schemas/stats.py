"""Gösterge paneli istatistik şemaları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BankCampaignCount(BaseModel):
    """Banka başına kampanya sayısı."""

    bank_code: str
    bank_name: str
    count: int


class CategoryCount(BaseModel):
    """Kategori başına kampanya sayısı.

    `category` PART 1'de daima null'dur (sitelerde kategori etiketi yok);
    bu satır "sınıflandırılmamış" anlamına gelir.
    """

    category: str | None = None
    count: int


class StatsResponse(BaseModel):
    """Genel bakış sayfasının beslendiği istatistikler."""

    total_banks: int = Field(description="BDDK listesindeki tüm bankalar")
    banks_with_data: int = Field(description="En az bir kampanyası bulunan banka sayısı")
    total_campaigns: int
    active_campaigns: int
    upcoming_campaigns: int
    expired_campaigns: int
    unknown_status_campaigns: int = Field(
        description="Tarihi bulunamayan kampanyalar — 'süresi dolmuş' DEĞİLDİR"
    )
    campaigns_by_bank: list[BankCampaignCount]
    campaigns_by_category: list[CategoryCount]
    last_scrape_at: datetime | None = Field(
        default=None, description="Son tamamlanan kazımanın zamanı (Türkiye saati)"
    )
