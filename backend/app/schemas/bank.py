"""Banka yanıt şemaları."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BankBase(BaseModel):
    """Banka kaydının ortak alanları."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    legal_name: str | None = None
    website: str
    bddk_status: str = Field(description="active | pre_launch")
    tkbb_member: bool
    data_status: str = Field(description="rich | limited | none")
    brand_color: str | None = None
    notes: str | None = Field(
        default=None,
        description="Veri durumunun gerekçesi; kampanyası olmayan bankalarda doludur",
    )


class BankSummary(BankBase):
    """Liste yanıtında kullanılan banka özeti.

    `campaign_count` alanı, kampanyası olmayan bankalar için 0 döner ve bu
    bankalar listeden ÇIKARILMAZ (şartname 5.1: BDDK listesindeki kuruluşların
    tümü veri setinde bulunmalıdır).
    """

    campaign_count: int = 0


class BankDetail(BankSummary):
    """Banka detay yanıtı."""

    legacy_domains: list[str] | None = None
