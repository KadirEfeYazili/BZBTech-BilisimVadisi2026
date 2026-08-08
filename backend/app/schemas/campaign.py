"""Kampanya yanıt şemaları."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.bank import BankBase


class CampaignListItem(BaseModel):
    """Tablo görünümünde kullanılan kampanya özeti."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    bank_code: str
    bank_name: str
    external_slug: str
    title: str
    category: str | None = Field(
        default=None, description="PART 1'de daima null; PART 3'te sınıflandırılacak"
    )
    segment: str | None = None
    target_customer: str | None = None
    start_date: date | None = Field(
        default=None, description="Bilinmiyorsa null — tarih UYDURULMAZ"
    )
    end_date: date | None = None
    date_precision: str = Field(description="exact | partial | inferred | unknown")
    status: str = Field(description="active | upcoming | expired | unknown — BACKEND'de hesaplanır")
    source_url: str


class SourceDocumentSummary(BaseModel):
    """Kampanyanın çıkarıldığı ham dokümanın özeti (izlenebilirlik)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    canonical_url: str | None = None
    doc_type: str
    http_status: int | None = None
    fetched_at: datetime
    scraper_name: str | None = None
    scraper_version: str | None = None
    raw_html_sha256: str | None = None


class CampaignDetail(CampaignListItem):
    """Kampanya detay yanıtı."""

    description: str | None = None
    conditions_text: str | None = None
    exclusions_text: str | None = None
    participation_method: str | None = None
    participation_channel: str | None = None
    sms_keyword: str | None = None
    sms_number: str | None = None
    coupon_code: str | None = None
    is_archived: bool = False
    first_seen_at: datetime
    last_seen_at: datetime
    bank: BankBase
    source_document: SourceDocumentSummary | None = None
