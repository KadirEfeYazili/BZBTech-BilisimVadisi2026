"""Alembic ortam betiği.

Veritabanı adresini `alembic.ini`den değil `get_settings()`ten okur; tek doğruluk
kaynağı .env dosyasıdır. SQLite'ta ALTER TABLE desteği kısıtlı olduğu için
`render_as_batch=True` kullanılır — bu sayede `alembic downgrade` de çalışır.
"""

from __future__ import annotations

from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db.base import Base, UtcDateTime

# Tüm modelleri içe aktarmak Base.metadata'yı doldurur — autogenerate için zorunlu.
import app.db.models  # noqa: F401

config = context.config


def render_item(type_: str, obj: Any, autogen_context: Any) -> str | bool:
    """Özel sütun tiplerini migration dosyasına saf SQLAlchemy tipi olarak yazar.

    `UtcDateTime` veritabanı seviyesinde `DateTime(timezone=True)`dır. Böyle
    yazılması, migration dosyalarının uygulama koduna bağımlı olmasını önler:
    uygulama tipi sonradan değişse bile geçmiş göçler çalışmaya devam eder.
    """
    if type_ == "type" and isinstance(obj, UtcDateTime):
        return "sa.DateTime(timezone=True)"
    return False

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Bağlantı adresini ayarlardan al.
config.set_main_option("sqlalchemy.url", get_settings().sqlalchemy_url)


def run_migrations_offline() -> None:
    """Bağlantı açmadan SQL betiği üretir (--sql modu)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Canlı bağlantı üzerinden göçleri uygular."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # SQLite'ta kısıt/kolon değişikliği için tablo yeniden oluşturma stratejisi.
            render_as_batch=True,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
