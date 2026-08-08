"""Tüm ORM modelleri.

Alembic'in şemayı görebilmesi için her model bu modülden export edilir.
"""

from app.db.models.bank import BDDK_STATUSES, DATA_STATUSES, Bank
from app.db.models.campaign import (
    CAMPAIGN_STATUSES,
    DATE_PRECISIONS,
    PARTICIPATION_METHODS,
    SEGMENTS,
    Campaign,
)
from app.db.models.campaign_extraction import EXTRACTION_METHODS, CampaignExtraction
from app.db.models.campaign_metric import CampaignMetric
from app.db.models.glossary import GlossaryTerm
from app.db.models.product import Product, ProductRate
from app.db.models.scrape_run import SCRAPE_RUN_STATUSES, ScrapeRun
from app.db.models.source_document import DISCOVERY_METHODS, DOC_TYPES, SourceDocument

__all__ = [
    "BDDK_STATUSES",
    "CAMPAIGN_STATUSES",
    "DATA_STATUSES",
    "DATE_PRECISIONS",
    "DISCOVERY_METHODS",
    "DOC_TYPES",
    "EXTRACTION_METHODS",
    "PARTICIPATION_METHODS",
    "SCRAPE_RUN_STATUSES",
    "SEGMENTS",
    "Bank",
    "Campaign",
    "CampaignExtraction",
    "CampaignMetric",
    "GlossaryTerm",
    "Product",
    "ProductRate",
    "ScrapeRun",
    "SourceDocument",
]
