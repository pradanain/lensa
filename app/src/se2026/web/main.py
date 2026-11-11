import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from ..analytics.registry import AnalyticsError
from .database import AppDatabase
from .directory import DirectoryIndex
from .questionnaire import Questionnaires
from .references import References
from .routers import analytics, quality, records, references
from .security import router as auth_router
from .settings import Settings


def create_app(settings=None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        if settings.environment == "production":
            with app.state.app_db.connection() as con:
                if not con.execute("SELECT 1 FROM users WHERE role='admin' AND active=1 LIMIT 1").fetchone():
                    raise RuntimeError("PRODUCTION_ADMIN_NOT_PROVISIONED")
        if settings.build_index_on_start:
            app.state.directory.ensure()
        yield

    app = FastAPI(
        title="SE2026 Bulungan — Portal Eksplorasi",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings
    app.state.app_db = AppDatabase(settings)
    app.state.references = References(settings.root)
    app.state.directory = DirectoryIndex(settings, app.state.app_db, app.state.references)
    app.state.questionnaires = Questionnaires(settings, app.state.references)
    app.state.aggregate_cache = analytics.AggregateCache(settings)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    @app.middleware("http")
    async def privacy_headers(request: Request, call_next):
        # No request/query/body/exception values are logged here.
        try:
            response = await call_next(request)
        except Exception:
            response = JSONResponse(
                status_code=500, content={"detail": "INTERNAL_ERROR_NO_SOURCE_VALUES_LOGGED"}
            )
        if request.url.path.startswith("/assets/") and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-store, private"
            response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # FastAPI's default includes the rejected input, which may be a password
        # or respondent identifier. Return field names and safe codes only.
        return JSONResponse(
            status_code=422,
            content={"detail": "INVALID_REQUEST", "fields": [str(e["loc"][-1]) for e in exc.errors()]},
        )

    @app.exception_handler(AnalyticsError)
    async def analytics_error(request, exc):
        return JSONResponse(status_code=422, content={"detail": "ANALYTICAL_QUERY_NOT_ALLOWED"})

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        return JSONResponse(status_code=500, content={"detail": "INTERNAL_ERROR_NO_SOURCE_VALUES_LOGGED"})

    # Suppress verbose framework/request logging; operational evidence uses
    # normalized action codes in the private application database.
    logging.getLogger("uvicorn.access").disabled = True
    for router in [auth_router, records.router, analytics.router, references.router, quality.router]:
        app.include_router(router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "census": "read_only"}

    @app.get("/api/ready")
    def ready():
        from .database import census_connection

        try:
            with census_connection(settings) as con:
                con.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
            with app.state.app_db.connection() as con:
                if (
                    settings.environment == "production"
                    and not con.execute(
                        "SELECT 1 FROM users WHERE role='admin' AND active=1 LIMIT 1"
                    ).fetchone()
                ):
                    return JSONResponse(status_code=503, content={"status": "not_ready"})
            return {"status": "ready"}
        except Exception:
            return JSONResponse(status_code=503, content={"status": "not_ready"})

    web = settings.root / "app/web/dist"
    if (web / "assets").exists():
        app.mount(
            "/assets",
            GZipMiddleware(StaticFiles(directory=web / "assets"), minimum_size=1024, compresslevel=5),
            name="assets",
        )

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "ENDPOINT_NOT_FOUND"})
        if not (web / "index.html").exists():
            return JSONResponse(status_code=503, content={"detail": "FRONTEND_BUILD_REQUIRED"})
        if not path:
            return RedirectResponse("/usaha", status_code=307)
        isolated = settings.business_focus_enabled and (
            path in ("dashboard", "keluarga", "data") or path.startswith(("dashboard/", "keluarga/", "data/"))
        )
        return FileResponse(web / "index.html", status_code=403 if isolated else 200)

    return app
