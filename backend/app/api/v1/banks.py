"""Banka uçları."""

from __future__ import annotations

from fastapi import APIRouter, Path

from app.api.deps import DbSession
from app.schemas.bank import BankDetail, BankSummary
from app.services.bank_service import get_bank, list_banks

router = APIRouter(prefix="/banks", tags=["bankalar"])


@router.get("", response_model=list[BankSummary], summary="Tüm bankalar")
def read_banks(session: DbSession) -> list[BankSummary]:
    """BDDK listesindeki tüm katılım bankalarını kampanya sayılarıyla döndürür.

    Kampanya sayfası bulunmayan bankalar (Adil Katılım) da
    listede yer alır ve `campaign_count=0` döner. "Veri yok" bilgisi de bir
    bulgudur; bu bankaları gizlemek veri setini eksik gösterirdi.
    """
    summaries: list[BankSummary] = []
    for bank, count in list_banks(session):
        summary = BankSummary.model_validate(bank)
        summary.campaign_count = count
        summaries.append(summary)
    return summaries


@router.get("/{code}", response_model=BankDetail, summary="Banka detayı")
def read_bank(
    session: DbSession,
    code: str = Path(description="Banka kodu (ör. emlak_katilim)"),
) -> BankDetail:
    """Tek bir bankanın detayını döndürür."""
    bank, count = get_bank(session, code)
    detail = BankDetail.model_validate(bank)
    detail.campaign_count = count
    return detail
