"""Kazıma komut satırı arayüzü.

Kullanım:
    python -m app.scrapers.run --banka emlak_katilim
    python -m app.scrapers.run --tumu
    python -m app.scrapers.run --banka emlak_katilim --dry-run
    python -m app.scrapers.run --banka ziraat_katilim --kategori kart-kampanyalari --limit 5
"""

from __future__ import annotations

import argparse
import sys
from typing import Final

from app.core.exceptions import AirgapError, AppError
from app.db.session import SessionLocal
from app.logging_config import configure_logging, get_logger
from app.scrapers.models import ScrapeRunResult
from app.scrapers.registry import available_banks, get_scraper

logger = get_logger(__name__)

# ANSI renk kodları — ek bağımlılık gerektirmez.
RESET: Final[str] = "\033[0m"
BOLD: Final[str] = "\033[1m"
DIM: Final[str] = "\033[2m"
GREEN: Final[str] = "\033[32m"
YELLOW: Final[str] = "\033[33m"
RED: Final[str] = "\033[31m"
CYAN: Final[str] = "\033[36m"

STATUS_COLORS: Final[dict[str, str]] = {
    "success": GREEN,
    "partial": YELLOW,
    "failed": RED,
    "running": CYAN,
}

COLUMNS: Final[tuple[tuple[str, int], ...]] = (
    ("Banka", 18),
    ("Durum", 10),
    ("Keşfedilen", 11),
    ("Çekilen", 9),
    ("Yeni", 6),
    ("Güncellenen", 12),
    ("Hata", 6),
)


def _supports_color() -> bool:
    """Terminal ANSI renklerini destekliyor mu?"""
    return sys.stdout.isatty()


def _colorize(text: str, color: str) -> str:
    """Renk destekleniyorsa metni renklendirir."""
    if not _supports_color():
        return text
    return f"{color}{text}{RESET}"


def _print_header() -> None:
    """Özet tablosunun başlık satırını yazar."""
    header = "".join(name.ljust(width) for name, width in COLUMNS)
    print(_colorize(header, BOLD))
    print(_colorize("-" * sum(width for _, width in COLUMNS), DIM))


def _print_row(result: ScrapeRunResult) -> None:
    """Tek bir çalıştırma sonucunu tablo satırı olarak yazar."""
    status_color = STATUS_COLORS.get(result.status, "")
    cells = (
        result.bank_code.ljust(COLUMNS[0][1]),
        _colorize(result.status.ljust(COLUMNS[1][1]), status_color),
        str(result.urls_discovered).ljust(COLUMNS[2][1]),
        str(result.urls_fetched).ljust(COLUMNS[3][1]),
        str(result.campaigns_new).ljust(COLUMNS[4][1]),
        str(result.campaigns_updated).ljust(COLUMNS[5][1]),
        _colorize(
            str(result.errors_count).ljust(COLUMNS[6][1]),
            RED if result.errors_count else "",
        ),
    )
    print("".join(cells))


def _print_errors(results: list[ScrapeRunResult]) -> None:
    """Hata özetlerini yazar."""
    for result in results:
        if not result.errors:
            continue
        print()
        print(_colorize(f"{result.bank_code} hataları ({result.errors_count} adet):", YELLOW))
        for message in result.errors[:10]:
            print(f"  - {message}")
        if result.errors_count > len(result.errors[:10]):
            kalan = result.errors_count - 10
            print(_colorize(f"  ... ve {kalan} hata daha", DIM))


def run_bank(
    bank_code: str,
    *,
    dry_run: bool,
    categories: list[str] | None = None,
    limit: int | None = None,
) -> ScrapeRunResult:
    """Tek bir bankanın scraper'ını çalıştırır.

    Args:
        bank_code: Banka kodu.
        dry_run: True ise veritabanına yazılmaz.
        categories: Yalnızca bu kategoriler taranır (destekleyen scraper'larda).
        limit: Çekilecek en fazla adres sayısı.

    Returns:
        Çalıştırma özeti.
    """
    scraper = get_scraper(bank_code, categories=categories, limit=limit)
    try:
        with SessionLocal() as session:
            return scraper.run(session, dry_run=dry_run)
    finally:
        scraper.close()


def main(argv: list[str] | None = None) -> int:
    """CLI girişi.

    Returns:
        Süreç çıkış kodu: 0 başarı, 1 kısmi/hatalı, 2 kullanım hatası.
    """
    parser = argparse.ArgumentParser(
        prog="python -m app.scrapers.run",
        description="Katılım bankası kampanya kazıyıcısı",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--bank",
        "--banka",
        dest="bank",
        help=f"Banka kodu ({', '.join(available_banks())})",
    )
    target.add_argument(
        "--all",
        "--tumu",
        dest="all",
        action="store_true",
        help="Kayıtlı tüm scraper'ları çalıştır",
    )
    parser.add_argument(
        "--kategori",
        action="append",
        dest="categories",
        metavar="AD",
        help="Yalnızca bu kategoriyi tara; birden çok kez verilebilir",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Çekilecek en fazla adres sayısı (pilot doğrulama için)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Veritabanına yazmadan yalnızca raporla",
    )

    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 1:
        parser.error("--limit en az 1 olmalıdır")
    # Kategori süzgeci tek bankada anlamlıdır: her bankanın kategori adları farklı.
    if args.categories and args.all:
        parser.error("--kategori yalnızca tek banka ile kullanılır (--banka)")
    configure_logging()

    # Windows konsolu varsayılan olarak cp1254 kullanır ve Türkçe karakterleri
    # bozar; çıktı akışı UTF-8'e alınır.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    bank_codes = available_banks() if args.all else [args.bank]

    results: list[ScrapeRunResult] = []
    print()
    if args.dry_run:
        print(_colorize("DRY-RUN: veritabanına hiçbir şey yazılmayacak.", YELLOW))
        print()
    _print_header()

    for bank_code in bank_codes:
        try:
            result = run_bank(
                bank_code,
                dry_run=args.dry_run,
                categories=args.categories,
                limit=args.limit,
            )
        except AirgapError as exc:
            print(_colorize(f"\n{exc.message}", RED))
            return 2
        except AppError as exc:
            print(_colorize(f"\n{bank_code}: {exc.message}", RED))
            return 2
        results.append(result)
        _print_row(result)

    _print_errors(results)
    print()

    has_problem = any(r.status != "success" for r in results)
    return 1 if has_problem else 0


if __name__ == "__main__":
    raise SystemExit(main())
