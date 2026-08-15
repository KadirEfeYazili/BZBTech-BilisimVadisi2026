"""kampanyalara bankanin kendi kategori etiketi

NEDEN AYRI SÜTUN: Bazı bankalar kampanyanın sektörünü kendisi yazıyor —
Ziraat Katılım liste kartında `<span class="item-category">Giyim ve Aksesuar</span>`,
Kuveyt Türk adres yolunda `/kart-kampanyalari/`. Bu etiket ÇIKARIM DEĞİL,
kaynak veridir ve sınıflandırmada güveni 1.00'dır.

Keşif sırasında `DiscoveredUrl.category_hint` içinde taşınıyordu ama hiçbir
yere yazılmıyordu; sınıflandırma adımına ulaşamıyordu. Ölçüldü: Ziraat'in 209
kampanyasının 153'ü gerçek bir sektöre eşlenebilecekken hepsi "genel"
kalıyordu.

⚠️ `campaigns.category` KULLANILMADI. O sütun nihai (çıkarılmış) sınıflandırma
için ayrılmış; bankanın ham etiketiyle karıştırılırsa "bu değer bankadan mı
geldi yoksa biz mi çıkardık" ayrımı kaybolur.

Sütunun ayrı tutulmasının ikinci nedeni: sınıflandırma AĞA ÇIKMADAN yeniden
çalıştırılabilmeli. Etiket yalnızca kazıma anında bellekte kalsaydı, sözlük
her genişletildiğinde bankalara yeniden istek atmak gerekirdi.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Şemayı ileri al."""
    with op.batch_alter_table("campaigns", schema=None) as batch_op:
        batch_op.add_column(sa.Column("bank_category", sa.Text(), nullable=True))


def downgrade() -> None:
    """Şemayı geri al."""
    with op.batch_alter_table("campaigns", schema=None) as batch_op:
        batch_op.drop_column("bank_category")
