"""Kampanya sınıflandırma komutu.

Kayıtlı veriden çalışır, AĞA ÇIKMAZ. Sözlük her genişletildiğinde yeniden
çalıştırılabilir; bankalara yeni istek gitmez.

Çalıştırma:
    python dev.py siniflandir
    python dev.py siniflandir --banka ziraat_katilim
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.logging_config import configure_logging
from app.services.taxonomy_service import build_report, categorize_campaigns

# backend/scripts/ -> backend/ -> depo kökü
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAPOR_YOLU = REPO_ROOT / "docs" / "taxonomy_report.md"

# Kapı eşiği: sektörü çıkarılamayan kampanya oranı bunun altında olmalı.
FALLBACK_LIMIT = 0.40


def main(argv: list[str] | None = None) -> int:
    """Betiğin giriş noktası."""
    ayristirici = argparse.ArgumentParser(description="Kampanya sınıflandırma")
    ayristirici.add_argument("--banka", help="Yalnızca bu bankayı sınıflandır")
    argumanlar = ayristirici.parse_args(argv)

    configure_logging()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    with SessionLocal() as session:
        sonuc = categorize_campaigns(session, bank_code=argumanlar.banka)

    if sonuc.campaigns == 0:
        print("Sınıflandırılacak kampanya bulunamadı. Önce 'python dev.py scrape' çalıştırın.")
        return 1

    print(f"\nKampanya          : {sonuc.campaigns}")
    print(f"Üretilen etiket   : {sonuc.labels}")
    print(f"Kanıt kaynağı     : {dict(sonuc.by_source)}")
    print(f"Ürün türü yok     : {sonuc.missing_product_type}")
    print(f"Sektörü 'genel'   : {sonuc.fallback_only} (%{100 * sonuc.fallback_ratio:.1f})")

    RAPOR_YOLU.parent.mkdir(parents=True, exist_ok=True)
    RAPOR_YOLU.write_text(build_report(sonuc), encoding="utf-8")
    print(f"\nRapor: {RAPOR_YOLU}")

    if sonuc.fallback_ratio >= FALLBACK_LIMIT:
        print(
            f"\nUYARI: 'genel' oranı %{100 * FALLBACK_LIMIT:.0f} eşiğinin üstünde. "
            "Sözlüğü genişletmek bu oranı düşürür (app/core/taxonomy.py)."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
