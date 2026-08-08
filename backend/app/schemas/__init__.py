"""API yanıt şemaları (Pydantic v2)."""

from app.schemas.bank import BankBase, BankDetail, BankSummary
from app.schemas.campaign import CampaignDetail, CampaignListItem, SourceDocumentSummary
from app.schemas.common import ErrorDetail, ErrorResponse, HealthResponse, Page
from app.schemas.stats import BankCampaignCount, CategoryCount, StatsResponse

__all__ = [
    "BankBase",
    "BankCampaignCount",
    "BankDetail",
    "BankSummary",
    "CampaignDetail",
    "CampaignListItem",
    "CategoryCount",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "Page",
    "SourceDocumentSummary",
    "StatsResponse",
]
