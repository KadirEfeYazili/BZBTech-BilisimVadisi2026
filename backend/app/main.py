"""FastAPI uygulaması: CORS, yönlendirici bağlama ve global hata yönetimi."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api.v1 import api_router
from app.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.logging_config import configure_logging, get_logger
from app.schemas.common import ErrorDetail, ErrorResponse

logger = get_logger(__name__)


def _error_response(
    status_code: int, code: str, message: str, detail: str | None = None
) -> JSONResponse:
    """Tek biçimli hata gövdesi üretir.

    Tüm hatalar aynı zarfla döner: {"error": {"code", "message", "detail"}}.
    Arayüz böylece hata tipini gövde biçiminden değil `code` alanından okur.
    """
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message, detail=detail))
    return JSONResponse(status_code=status_code, content=payload.model_dump())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Uygulama yaşam döngüsü."""
    configure_logging()
    settings = get_settings()
    logger.info(
        "uygulama_basladi",
        ortam=settings.app_env,
        surum=__version__,
        airgap=settings.airgap_mode,
    )
    yield
    logger.info("uygulama_kapandi")


def create_app() -> FastAPI:
    """FastAPI uygulamasını kurar ve döndürür."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Katılım bankalarının kampanya verilerini toplayan, normalize eden ve "
            "sunan platformun API'si."
        ),
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # ── Global hata yönetimi ──────────────────────────────

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        """Uygulama istisnalarını tek biçimli gövdeye çevirir."""
        if exc.status_code >= 500:
            logger.error("uygulama_hatasi", kod=exc.code, mesaj=exc.message, yol=request.url.path)
        else:
            logger.info("istemci_hatasi", kod=exc.code, mesaj=exc.message, yol=request.url.path)
        return _error_response(exc.status_code, exc.code, exc.message, exc.detail)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """FastAPI'nin ürettiği HTTP hatalarını aynı zarfa sokar."""
        codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 422: "VALIDATION_ERROR"}
        return _error_response(
            exc.status_code,
            codes.get(exc.status_code, "HTTP_ERROR"),
            str(exc.detail) if exc.detail else "İstek işlenemedi",
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Sorgu/gövde doğrulama hatalarını tek biçimli gövdeye çevirir."""
        return _error_response(
            422,
            "VALIDATION_ERROR",
            "İstek parametreleri geçersiz",
            detail=str(exc.errors()),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """Beklenmeyen hatalar: iç ayrıntı sızdırılmaz, sunucuda loglanır."""
        logger.error(
            "beklenmeyen_hata",
            hata=str(exc),
            tip=type(exc).__name__,
            yol=request.url.path,
        )
        detail = str(exc) if settings.debug else None
        return _error_response(500, "INTERNAL_ERROR", "Beklenmeyen bir hata oluştu", detail)

    _mount_frontend(app)

    return app


def _mount_frontend(app: FastAPI) -> None:
    """Derlenmiş frontend'i "/" altından servis eder.

    Tek port kuralı (§14): üretimde ayrı bir Node sunucusu çalıştırılmaz,
    Vite'ın ürettiği statik dosyalar FastAPI tarafından sunulur.

    İstemci tarafı yönlendirme (React Router) için bilinmeyen yollar
    `index.html`e düşürülür; ancak `/api` altındaki bilinmeyen yollar JSON 404
    döndürmeye devam eder — API istemcisine HTML göndermek hata ayıklamayı
    imkânsız hâle getirirdi.
    """
    settings = get_settings()
    dist = settings.frontend_dist_path

    if not dist.is_dir():
        logger.info(
            "frontend_dist_bulunamadi",
            yol=str(dist),
            not_="Geliştirmede normaldir; üretim için 'make build-web' çalıştırın.",
        )
        return

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    index_file = dist / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        """Statik dosyayı veya tek sayfa uygulamasının giriş dosyasını döndürür."""
        if full_path.startswith(("api/", "docs", "openapi.json")):
            raise NotFoundError(f"Uç bulunamadı: /{full_path}")

        candidate = (dist / full_path).resolve()
        # Dizin dışına çıkma (path traversal) denemelerine karşı koruma.
        if full_path and candidate.is_file() and candidate.is_relative_to(dist):
            return FileResponse(candidate)

        return FileResponse(index_file)

    logger.info("frontend_baglandi", yol=str(dist))


app = create_app()
