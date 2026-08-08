"""structlog tabanlı yapılandırılmış loglama.

KURAL (§11): `print()` yasak. Tüm çıktı structlog üzerinden akar.
Geliştirmede insan okunur renkli çıktı, üretimde JSON satırları üretilir.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.config import get_settings

_configured = False


def configure_logging(*, force: bool = False) -> None:
    """structlog'u ve standart kütüphane loglamasını yapılandırır.

    Args:
        force: True ise daha önce yapılandırılmış olsa dahi yeniden kurar.
    """
    global _configured
    if _configured and not force:
        return

    settings = get_settings()
    level = logging.DEBUG if settings.debug else logging.INFO

    # Standart kütüphane loglarını (uvicorn, sqlalchemy) stdout'a yönlendir.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    renderer: structlog.typing.Processor
    if settings.is_production:
        # Üretimde JSON: log toplayıcılar tarafından ayrıştırılabilir.
        shared_processors.append(structlog.processors.format_exc_info)
        renderer = structlog.processors.JSONRenderer(ensure_ascii=False)
    else:
        # Geliştirmede renkli, hizalı konsol çıktısı.
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """İsimlendirilmiş bir logger döndürür.

    Args:
        name: Genellikle `__name__`.
    """
    configure_logging()
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
