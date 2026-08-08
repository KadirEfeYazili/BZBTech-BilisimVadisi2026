#!/usr/bin/env python
"""Proje görev betiği — `make` gerektirmez.

Makefile ile aynı işleri yapar; Windows'ta `make` çoğu zaman kurulu olmadığı
için asıl giriş noktası budur. Ek bağımlılık kullanmaz, yalnızca standart
kütüphaneyle çalışır.

Kullanım:
    python dev.py kur          # bağımlılıkları kur (backend + frontend)
    python dev.py migrate      # veritabanı şemasını oluştur
    python dev.py seed         # 11 banka + terminoloji sözlüğü
    python dev.py api          # backend'i başlat  -> http://localhost:8000
    python dev.py web          # arayüzü başlat    -> http://localhost:5173
    python dev.py scrape       # tüm scraper'ları çalıştır
    python dev.py test         # testler + kapsam
    python dev.py lint         # ruff + mypy + tsc
    python dev.py baslat       # migrate + seed + api  (ilk kurulumdan sonra tek komut)

Komut listesi için:
    python dev.py
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

KOK = Path(__file__).resolve().parent
BACKEND = KOK / "backend"
FRONTEND = KOK / "frontend"
VENV = BACKEND / ".venv"

WINDOWS = platform.system() == "Windows"
VENV_PYTHON = VENV / ("Scripts/python.exe" if WINDOWS else "bin/python")


def _python() -> str:
    """Sanal ortamdaki Python'u döndürür; yoksa çalışan yorumlayıcıyı kullanır."""
    if VENV_PYTHON.is_file():
        return str(VENV_PYTHON)
    return sys.executable


def _npm() -> str:
    """npm çalıştırılabilirinin adını döndürür."""
    return "npm.cmd" if WINDOWS else "npm"


def _calistir(komut: list[str], *, cwd: Path = KOK) -> int:
    """Komutu çalıştırır ve çıkış kodunu döndürür."""
    yazdir = " ".join(komut)
    print(f"\n\033[36m$ {yazdir}\033[0m  (dizin: {cwd.relative_to(KOK) if cwd != KOK else '.'})")
    try:
        return subprocess.call(komut, cwd=cwd)
    except FileNotFoundError:
        print(f"\033[31mKomut bulunamadı: {komut[0]}\033[0m")
        return 127


def _zincir(*adimlar: Callable[[], int]) -> int:
    """Adımları sırayla çalıştırır; ilk hatada durur."""
    for adim in adimlar:
        kod = adim()
        if kod != 0:
            return kod
    return 0


# ── Görevler ──────────────────────────────────────────────


def kur() -> int:
    """Backend sanal ortamını ve frontend paketlerini kurar."""
    if not VENV_PYTHON.is_file():
        print("Sanal ortam oluşturuluyor...")
        kod = _calistir([sys.executable, "-m", "venv", str(VENV)])
        if kod != 0:
            return kod

    kod = _calistir([_python(), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    if kod != 0:
        return kod

    kod = _calistir([_python(), "-m", "pip", "install", "-e", ".[dev]"], cwd=BACKEND)
    if kod != 0:
        return kod

    if shutil.which(_npm()) is None:
        print("\033[33mnpm bulunamadı; frontend kurulumu atlandı.\033[0m")
        print("Node.js 20+ kurup 'python dev.py kur' komutunu tekrar çalıştırın.")
        return 0

    kod = _calistir([_npm(), "install"], cwd=FRONTEND)
    if kod != 0:
        return kod

    _env_dosyasi_olustur()
    print("\n\033[32mKurulum tamam.\033[0m Sıradaki: python dev.py baslat")
    return 0


def _env_dosyasi_olustur() -> None:
    """`.env` yoksa örnekten kopyalar."""
    env = KOK / ".env"
    ornek = KOK / ".env.example"
    if not env.exists() and ornek.exists():
        env.write_text(ornek.read_text(encoding="utf-8"), encoding="utf-8")
        print(".env dosyası .env.example'dan oluşturuldu.")


def migrate() -> int:
    """Veritabanı şemasını en son sürüme getirir."""
    return _calistir([_python(), "-m", "alembic", "upgrade", "head"], cwd=BACKEND)


def migrate_geri() -> int:
    """Son göçü geri alır."""
    return _calistir([_python(), "-m", "alembic", "downgrade", "-1"], cwd=BACKEND)


def seed() -> int:
    """11 bankayı ve terminoloji sözlüğünü yükler (tekrar çalıştırılabilir)."""
    return _calistir([_python(), "-m", "app.db.seed"], cwd=BACKEND)


def api() -> int:
    """Backend'i geliştirme kipinde başlatır."""
    print("\nBackend: http://localhost:8000  ·  API dokümanı: http://localhost:8000/docs")
    return _calistir(
        [_python(), "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
        cwd=BACKEND,
    )


def web() -> int:
    """Arayüz geliştirme sunucusunu başlatır."""
    print("\nArayüz: http://localhost:5173")
    return _calistir([_npm(), "run", "dev"], cwd=FRONTEND)


def scrape() -> int:
    """Kayıtlı tüm scraper'ları çalıştırır."""
    return _calistir([_python(), "-m", "app.scrapers.run", "--all"], cwd=BACKEND)


def scrape_deneme() -> int:
    """Kazımayı veritabanına yazmadan dener."""
    return _calistir(
        [_python(), "-m", "app.scrapers.run", "--all", "--dry-run"], cwd=BACKEND
    )


def test() -> int:
    """Testleri kapsam raporuyla çalıştırır."""
    return _calistir(
        [
            _python(),
            "-m",
            "pytest",
            "tests",
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-fail-under=60",
        ],
        cwd=BACKEND,
    )


def lint() -> int:
    """Biçim, kural ve tip denetimi yapar."""
    kod = _zincir(
        lambda: _calistir([_python(), "-m", "ruff", "check", "app", "tests"], cwd=BACKEND),
        lambda: _calistir(
            [_python(), "-m", "ruff", "format", "--check", "app", "tests"], cwd=BACKEND
        ),
        lambda: _calistir([_python(), "-m", "mypy", "app"], cwd=BACKEND),
    )
    if kod != 0:
        return kod

    if shutil.which(_npm()) is None:
        print("\033[33mnpm bulunamadı; arayüz tip denetimi atlandı.\033[0m")
        return 0
    return _calistir([_npm(), "run", "typecheck"], cwd=FRONTEND)


def bicimle() -> int:
    """Kodu biçimlendirir."""
    return _zincir(
        lambda: _calistir([_python(), "-m", "ruff", "format", "app", "tests"], cwd=BACKEND),
        lambda: _calistir(
            [_python(), "-m", "ruff", "check", "--fix", "app", "tests"], cwd=BACKEND
        ),
    )


def derle_web() -> int:
    """Arayüzü derler; backend bu çıktıyı "/" altından sunar."""
    return _calistir([_npm(), "run", "build"], cwd=FRONTEND)


def baslat() -> int:
    """Şemayı hazırlar, veriyi yükler ve backend'i başlatır."""
    return _zincir(migrate, seed, api)


GOREVLER: dict[str, tuple[Callable[[], int], str]] = {
    "kur": (kur, "Bağımlılıkları kurar (backend + frontend)"),
    "baslat": (baslat, "migrate + seed + api — ilk kurulumdan sonra tek komut"),
    "migrate": (migrate, "Veritabanı şemasını oluşturur/günceller"),
    "migrate-geri": (migrate_geri, "Son göçü geri alır"),
    "seed": (seed, "11 banka + terminoloji sözlüğünü yükler"),
    "api": (api, "Backend'i başlatır (http://localhost:8000)"),
    "web": (web, "Arayüzü başlatır (http://localhost:5173)"),
    "scrape": (scrape, "Tüm scraper'ları çalıştırır"),
    "scrape-deneme": (scrape_deneme, "Kazımayı veritabanına yazmadan dener"),
    "test": (test, "Testleri kapsam raporuyla çalıştırır"),
    "lint": (lint, "ruff + mypy + tsc denetimi"),
    "bicimle": (bicimle, "Kodu biçimlendirir"),
    "derle-web": (derle_web, "Arayüzü üretim için derler"),
}


def _yardim() -> int:
    """Komut listesini yazar."""
    print(__doc__.split("Kullanım:")[0].strip())
    print("\nKomutlar:\n")
    for ad, (_, aciklama) in GOREVLER.items():
        print(f"  \033[36m{ad:16s}\033[0m {aciklama}")
    print("\nÖrnek:  python dev.py baslat\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Betiğin giriş noktası."""
    if WINDOWS:
        # Windows konsolunda ANSI renkleri ve Türkçe karakterler için.
        os.system("")  # noqa: S605  (renk desteğini etkinleştirir)
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")

    argumanlar = argv if argv is not None else sys.argv[1:]
    if not argumanlar or argumanlar[0] in ("-h", "--help", "yardim"):
        return _yardim()

    ad = argumanlar[0]
    gorev = GOREVLER.get(ad)
    if gorev is None:
        print(f"\033[31mBilinmeyen komut: {ad}\033[0m\n")
        return _yardim() or 2

    return gorev[0]()


if __name__ == "__main__":
    raise SystemExit(main())
