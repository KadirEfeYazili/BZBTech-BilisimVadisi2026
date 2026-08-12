"""urun varyantlari, kampanya taksonomisi, hesaplayici envanteri

SPRINT 2 

Bu göç MEVCUT VERİYİ KORUR: `campaigns` ve `source_documents` tablolarına
dokunulmaz, yalnızca yeni sütun ve tablolar eklenir.

⚠️ Kontrollü sözlük değerleri burada BİREBİR yazılıdır, `app/core/vocab.py`'den
import EDİLMEZ. Göç dosyası şemanın donmuş bir anlık görüntüsüdür; uygulama
sözlüğü sonradan genişlediğinde bu göçün ürettiği şema değişmemelidir.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ── Kontrollü sözlükler (0002 anındaki hâliyle) ───────────
VARIANT_DIMENSIONS = "'arac_durumu', 'konut_durumu', 'enerji_sinifi', 'sigorta', 'musteri_tipi', 'ozel'"  # noqa: E501
VARIANT_SOURCES = "'dropdown_option', 'separate_page', 'table_column', 'text'"
LIMIT_SOURCES = "'html_attr', 'html_table', 'text', 'calculator', 'none'"
COLLATERAL_TYPES = "'konut', 'tasit', 'yok', 'diger'"
RATE_SOURCES = "'html_table', 'payment_plan_derived', 'calculator_api', 'calculator_playwright', 'text', 'js_default', 'none'"  # noqa: E501
TAXONOMY_AXES = "'product_type', 'sector', 'audience', 'benefit'"
CATEGORY_SOURCES = "'url', 'bank_category', 'keyword', 'merchant', 'llm'"
CALCULATOR_MECHANISMS = "'api', 'js_client_side', 'js_with_rate_fetch', 'unknown', 'none'"
SAMPLING_DECISIONS = "'full', 'grid', 'pilot_only', 'skip'"
PROBE_METHODS = "'api', 'js_default', 'playwright', 'payment_plan_derived'"

# Bu göçte `products` ve `product_rates`'e eklenen sütunlar. `downgrade`
# aynı listeyi kullanır; iki yerde ayrı ayrı yazılırsa biri unutulur.
PRODUCT_COLUMNS = (
    "parent_product_id",
    "variant_key",
    "variant_label",
    "variant_dimension",
    "variant_source",
    "amount_min",
    "amount_max",
    "term_months_min",
    "term_months_max",
    "allowed_terms",
    "ltv_max_pct",
    "collateral_type",
    "currency",
    "has_calculator",
    "calculator_url",
    "limits_source",
    "limits_evidence",
    "is_binding",
    "non_binding_notice",
)

PRODUCT_RATE_COLUMNS = (
    "amount_min",
    "amount_max",
    "ltv_band_min_pct",
    "ltv_band_max_pct",
    "energy_class",
    "vehicle_age_min",
    "vehicle_age_max",
    "rate_source",
    "confidence",
    "source_document_id",
    "evidence_text",
)

# Bu göçün eklediği CHECK kısıtları (`ck_<tablo>_` ön eki olmadan).
PRODUCT_CHECKS = (
    "variant_dimension_valid",
    "variant_source_valid",
    "limits_source_valid",
    "collateral_type_valid",
    "amount_range_valid",
    "term_range_valid",
)

PRODUCT_RATE_CHECKS = (
    "rate_source_valid",
    "confidence_range_valid",
    "rate_amount_range_valid",
    "vehicle_age_range_valid",
)


def upgrade() -> None:
    """Şemayı ileri al."""
    _upgrade_products()
    _upgrade_product_rates()
    _create_campaign_categories()
    _create_calculator_inventory()
    _create_calculator_probes()


def downgrade() -> None:
    """Şemayı geri al.

    Yeni tablolar düşürülür, eklenen sütunlar kaldırılır. `campaigns` ve
    `source_documents` bu göçte hiç değişmediği için toplanmış kampanya
    verisi geri alma sırasında da korunur.
    """
    op.drop_table("calculator_probes")
    op.drop_table("calculator_inventory")
    op.drop_table("campaign_categories")

    # ⚠️ Kısıtlar sütunlardan ÖNCE düşürülür. SQLite'ta `ALTER TABLE ... DROP
    # COLUMN` yoktur; Alembic tabloyu yansıtıp yeniden kurar. Yansıtılan CHECK
    # kısıtları düşürülen sütunlara atıf yaptığı için, önce kaldırılmazlarsa
    # yeniden kurma "no such column: amount_max" ile başarısız olur.
    with op.batch_alter_table("product_rates", schema=None) as batch_op:
        # `batch_op.f(...)`: ad zaten nihaidir, isimlendirme konvansiyonu
        # tekrar ön ek eklemesin.
        for constraint in PRODUCT_RATE_CHECKS:
            batch_op.drop_constraint(batch_op.f(f"ck_product_rates_{constraint}"), type_="check")
        batch_op.drop_constraint(
            batch_op.f("fk_product_rates_source_document_id_source_documents"),
            type_="foreignkey",
        )
        batch_op.drop_index("ix_product_rates_product_id_term_months")
        for column in PRODUCT_RATE_COLUMNS:
            batch_op.drop_column(column)

    with op.batch_alter_table("products", schema=None) as batch_op:
        for constraint in PRODUCT_CHECKS:
            batch_op.drop_constraint(batch_op.f(f"ck_products_{constraint}"), type_="check")
        batch_op.drop_constraint(
            batch_op.f("fk_products_parent_product_id_products"), type_="foreignkey"
        )
        batch_op.drop_index("ix_products_bank_id_product_type")
        batch_op.drop_index(batch_op.f("ix_products_variant_key"))
        batch_op.drop_index(batch_op.f("ix_products_parent_product_id"))
        for column in PRODUCT_COLUMNS:
            batch_op.drop_column(column)


# ── Adımlar ───────────────────────────────────────────────


def _upgrade_products() -> None:
    """`products`'a varyant boyutunu ve limit alanlarını ekler."""
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.add_column(sa.Column("parent_product_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("variant_key", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("variant_label", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("variant_dimension", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("variant_source", sa.Text(), nullable=True))

        batch_op.add_column(sa.Column("amount_min", sa.Numeric(16, 2), nullable=True))
        batch_op.add_column(sa.Column("amount_max", sa.Numeric(16, 2), nullable=True))
        batch_op.add_column(sa.Column("term_months_min", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("term_months_max", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("allowed_terms", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("ltv_max_pct", sa.Numeric(6, 3), nullable=True))
        batch_op.add_column(sa.Column("collateral_type", sa.Text(), nullable=True))
        # NOT NULL sütunlar mevcut satırlar için sunucu varsayılanıyla doldurulur.
        batch_op.add_column(
            sa.Column("currency", sa.Text(), nullable=False, server_default="TRY")
        )

        batch_op.add_column(
            sa.Column(
                "has_calculator", sa.Boolean(), nullable=False, server_default=sa.text("0")
            )
        )
        batch_op.add_column(sa.Column("calculator_url", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("limits_source", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("limits_evidence", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("is_binding", sa.Boolean(), nullable=False, server_default=sa.text("1"))
        )
        batch_op.add_column(sa.Column("non_binding_notice", sa.Text(), nullable=True))

        batch_op.create_foreign_key(
            batch_op.f("fk_products_parent_product_id_products"),
            "products",
            ["parent_product_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_check_constraint(
            "variant_dimension_valid", f"variant_dimension IN ({VARIANT_DIMENSIONS})"
        )
        batch_op.create_check_constraint(
            "variant_source_valid", f"variant_source IN ({VARIANT_SOURCES})"
        )
        batch_op.create_check_constraint(
            "limits_source_valid", f"limits_source IN ({LIMIT_SOURCES})"
        )
        batch_op.create_check_constraint(
            "collateral_type_valid", f"collateral_type IN ({COLLATERAL_TYPES})"
        )
        batch_op.create_check_constraint(
            "amount_range_valid",
            "amount_min IS NULL OR amount_max IS NULL OR amount_min <= amount_max",
        )
        batch_op.create_check_constraint(
            "term_range_valid",
            "term_months_min IS NULL OR term_months_max IS NULL "
            "OR term_months_min <= term_months_max",
        )
        batch_op.create_index(
            batch_op.f("ix_products_parent_product_id"), ["parent_product_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_products_variant_key"), ["variant_key"], unique=False)
        batch_op.create_index(
            "ix_products_bank_id_product_type", ["bank_id", "product_type"], unique=False
        )


def _upgrade_product_rates() -> None:
    """`product_rates`'e bant boyutunu ve zorunlu kaynak alanını ekler."""
    with op.batch_alter_table("product_rates", schema=None) as batch_op:
        batch_op.add_column(sa.Column("amount_min", sa.Numeric(16, 2), nullable=True))
        batch_op.add_column(sa.Column("amount_max", sa.Numeric(16, 2), nullable=True))
        batch_op.add_column(sa.Column("ltv_band_min_pct", sa.Numeric(6, 3), nullable=True))
        batch_op.add_column(sa.Column("ltv_band_max_pct", sa.Numeric(6, 3), nullable=True))
        batch_op.add_column(sa.Column("energy_class", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("vehicle_age_min", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("vehicle_age_max", sa.Integer(), nullable=True))

        # Mevcut satırlar bankaların yayımladığı HTML oran tablolarından
        # geldiği için `html_table` ile geri doldurulur.
        batch_op.add_column(
            sa.Column("rate_source", sa.Text(), nullable=False, server_default="html_table")
        )
        batch_op.add_column(
            sa.Column(
                "confidence", sa.Numeric(4, 3), nullable=False, server_default=sa.text("1.000")
            )
        )
        batch_op.add_column(sa.Column("source_document_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("evidence_text", sa.Text(), nullable=True))

        batch_op.create_foreign_key(
            batch_op.f("fk_product_rates_source_document_id_source_documents"),
            "source_documents",
            ["source_document_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_check_constraint("rate_source_valid", f"rate_source IN ({RATE_SOURCES})")
        batch_op.create_check_constraint(
            "confidence_range_valid", "confidence >= 0 AND confidence <= 1"
        )
        batch_op.create_check_constraint(
            "rate_amount_range_valid",
            "amount_min IS NULL OR amount_max IS NULL OR amount_min <= amount_max",
        )
        batch_op.create_check_constraint(
            "vehicle_age_range_valid",
            "vehicle_age_min IS NULL OR vehicle_age_max IS NULL "
            "OR vehicle_age_min <= vehicle_age_max",
        )
        batch_op.create_index(
            "ix_product_rates_product_id_term_months", ["product_id", "term_months"], unique=False
        )

    # Sunucu varsayılanı YALNIZCA geri doldurma içindi. Kalıcı bırakılırsa,
    # kaynağı belirtilmeyen bir oran sessizce "html_table" (güven 1.00) sayılır
    # ve karşılaştırmada en yüksek önceliği alır — bu, kaynağı kayıt altına
    # alma güvencesini boşa çıkarır.
    with op.batch_alter_table("product_rates", schema=None) as batch_op:
        batch_op.alter_column("rate_source", server_default=None)


def _create_campaign_categories() -> None:
    """Çok eksenli kampanya taksonomisi tablosunu oluşturur."""
    op.create_table(
        "campaign_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("axis", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"axis IN ({TAXONOMY_AXES})", name=op.f("ck_campaign_categories_axis_valid")
        ),
        sa.CheckConstraint(
            f"source IN ({CATEGORY_SOURCES})", name=op.f("ck_campaign_categories_source_valid")
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_campaign_categories_confidence_range_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_campaign_categories_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaign_categories")),
        sa.UniqueConstraint(
            "campaign_id", "axis", "value", name="uq_campaign_categories_campaign_id_axis_value"
        ),
    )
    with op.batch_alter_table("campaign_categories", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_campaign_categories_campaign_id"), ["campaign_id"], unique=False
        )
        batch_op.create_index(
            "ix_campaign_categories_axis_value", ["axis", "value"], unique=False
        )


def _create_calculator_inventory() -> None:
    """Hesaplayıcı envanteri tablosunu oluşturur."""
    op.create_table(
        "calculator_inventory",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("page_url", sa.Text(), nullable=False),
        sa.Column("calculator_name", sa.Text(), nullable=True),
        sa.Column("input_fields", sa.JSON(), nullable=False),
        sa.Column("variant_count", sa.Integer(), nullable=True),
        sa.Column("amount_min", sa.Numeric(16, 2), nullable=True),
        sa.Column("amount_max", sa.Numeric(16, 2), nullable=True),
        sa.Column("allowed_terms", sa.JSON(), nullable=True),
        sa.Column("mechanism", sa.Text(), nullable=False),
        sa.Column("endpoint_url", sa.Text(), nullable=True),
        sa.Column("endpoint_method", sa.Text(), nullable=True),
        sa.Column("request_template", sa.JSON(), nullable=True),
        sa.Column("response_fields", sa.JSON(), nullable=True),
        sa.Column("total_combinations", sa.Integer(), nullable=True),
        sa.Column("sampling_decision", sa.Text(), nullable=True),
        sa.Column("feasible", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("non_binding_notice", sa.Text(), nullable=True),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"mechanism IN ({CALCULATOR_MECHANISMS})",
            name=op.f("ck_calculator_inventory_mechanism_valid"),
        ),
        sa.CheckConstraint(
            f"sampling_decision IN ({SAMPLING_DECISIONS})",
            name=op.f("ck_calculator_inventory_sampling_decision_valid"),
        ),
        sa.CheckConstraint(
            "amount_min IS NULL OR amount_max IS NULL OR amount_min <= amount_max",
            name=op.f("ck_calculator_inventory_amount_range_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["bank_id"],
            ["banks.id"],
            name=op.f("fk_calculator_inventory_bank_id_banks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calculator_inventory")),
        sa.UniqueConstraint(
            "bank_id", "page_url", name="uq_calculator_inventory_bank_id_page_url"
        ),
    )
    with op.batch_alter_table("calculator_inventory", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_calculator_inventory_bank_id"), ["bank_id"], unique=False
        )


def _create_calculator_probes() -> None:
    """Hesaplayıcı sorgu kayıtları tablosunu oluşturur."""
    op.create_table(
        "calculator_probes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("inventory_id", sa.Integer(), nullable=True),
        sa.Column("probe_amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("probe_term_months", sa.Integer(), nullable=False),
        sa.Column("probe_variant", sa.Text(), nullable=True),
        sa.Column("profit_rate_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("monthly_installment", sa.Numeric(16, 2), nullable=True),
        sa.Column("total_repayment", sa.Numeric(16, 2), nullable=True),
        sa.Column("total_profit_share", sa.Numeric(16, 2), nullable=True),
        sa.Column("allocation_fee", sa.Numeric(16, 2), nullable=True),
        sa.Column("insurance_fee", sa.Numeric(16, 2), nullable=True),
        sa.Column("annual_cost_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("endpoint_url", sa.Text(), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=True),
        sa.Column("response_raw", sa.Text(), nullable=True),
        sa.Column("probed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_binding", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"method IN ({PROBE_METHODS})", name=op.f("ck_calculator_probes_method_valid")
        ),
        sa.CheckConstraint(
            "probe_amount > 0", name=op.f("ck_calculator_probes_probe_amount_positive")
        ),
        sa.CheckConstraint(
            "probe_term_months > 0",
            name=op.f("ck_calculator_probes_probe_term_months_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["bank_id"],
            ["banks.id"],
            name=op.f("fk_calculator_probes_bank_id_banks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_id"],
            ["calculator_inventory.id"],
            name=op.f("fk_calculator_probes_inventory_id_calculator_inventory"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_calculator_probes_product_id_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calculator_probes")),
        sa.UniqueConstraint(
            "product_id",
            "probe_amount",
            "probe_term_months",
            "probe_variant",
            name="uq_calculator_probes_product_id_probe_amount",
        ),
    )
    with op.batch_alter_table("calculator_probes", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_calculator_probes_bank_id"), ["bank_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_calculator_probes_product_id"), ["product_id"], unique=False
        )
        batch_op.create_index(
            "ix_calculator_probes_bank_id_product_id", ["bank_id", "product_id"], unique=False
        )
