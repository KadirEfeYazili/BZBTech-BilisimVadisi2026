"""Playwright sarmalayıcısı — OPSİYONEL bağımlılık.

NEDEN OPSİYONEL: Değerlendirmenin %20'si "On-Prem Uygulanabilirlik" ve bunun
bir ölçütü harici bağımlılığın düşük olması. Playwright ~400 MB tarayıcı
indiriyor; bunu zorunlu kurulum adımı yapmak kapalı ağ kurulumunu ciddi
biçimde zorlaştırır.

Bu yüzden:
  - `python dev.py kur`             → Playwright İNDİRMEZ
  - `python dev.py kur --playwright` → ayrıca indirir

KURAL: Playwright gerektiren hiçbir kod, Playwright yoksa ÇÖKMEZ. Uyarı
loglanır, çağıran tarafa "kullanılamıyor" bilgisi döner ve akış devam eder.
Tek bir bankanın keşfi yapılamadığı için tüm sprint durmaz.

Bu modül yalnızca KEŞİF için kullanılır. Kampanya çekimi httpx ile yapılır:
detay sayfalarının tamamı sunucuda render ediliyor, tarayıcıya gerek yok.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from app.config import Settings, get_settings
from app.core.exceptions import AirgapError
from app.logging_config import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

# Tarayıcının sayfa yüklemesi için beklenecek en uzun süre.
DEFAULT_TIMEOUT_MS = 30_000

# Sayfa yüklendikten sonra ağ trafiğinin durulması için beklenen süre.
# Kampanya listeleri açılıştan hemen sonra XHR atıyor; bu pencere olmadan
# istekler kaçırılır.
NETWORK_IDLE_MS = 3_000


def is_playwright_available() -> bool:
    """Playwright'ın kurulu ve kullanılabilir olup olmadığını söyler.

    Yalnızca paketin varlığına bakar; tarayıcı ikilisinin indirilmiş olup
    olmadığı ancak açmayı denerken anlaşılır.

    Returns:
        Playwright içe aktarılabiliyorsa True.

    """
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    return True


def playwright_kurulum_mesaji() -> str:
    """Playwright yokken kullanıcıya gösterilecek yönergeyi döndürür."""
    return (
        "Playwright kurulu değil. Keşif için gereklidir:\n"
        "    python dev.py kur --playwright\n"
        "Kurulmadan devam edilirse ilgili bankalar mechanism='unknown', "
        "sampling_decision='skip' ile kaydedilir."
    )


@contextmanager
def browser_page(
    *,
    settings: Settings | None = None,
    on_response: Callable[[Any], None] | None = None,
) -> Iterator[Any]:
    """Tek kullanımlık bir tarayıcı sayfası açar.

    Args:
        settings: Uygulama ayarları; verilmezse `get_settings()` kullanılır.
        on_response: Her HTTP yanıtı için çağrılacak dinleyici. Ağ trafiğini
            gözlemleyip JSON dönen uçları yakalamak için kullanılır.

    Yields:
        Playwright `Page` nesnesi.

    Raises:
        AirgapError: `AIRGAP_MODE` açıkken dış ağa çıkma girişimi.
        RuntimeError: Playwright kurulu değilse.

    """
    settings = settings or get_settings()

    # Kapalı ağ kurulumunda sistemin dışarı hiç çıkmadığı garanti edilir;
    # bu denetim httpx tarafındakiyle aynı sözleşmeyi tarayıcıya da uygular.
    if settings.airgap_mode:
        raise AirgapError("AIRGAP_MODE açık; tarayıcı ile dış ağa çıkılamaz.")

    if not is_playwright_available():
        raise RuntimeError(playwright_kurulum_mesaji())

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                # Kimliğimizi gizlemiyoruz: bu siteler gerçek bankalara ait.
                user_agent=settings.scraper_user_agent,
                locale="tr-TR",
            )
            page = context.new_page()
            page.set_default_timeout(DEFAULT_TIMEOUT_MS)
            if on_response is not None:
                page.on("response", on_response)
            try:
                yield page
            finally:
                context.close()
        finally:
            browser.close()
