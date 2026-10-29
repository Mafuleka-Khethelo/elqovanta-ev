"""Elqovanta EV API.

Cookie sessions are protected by a double-submit CSRF token. The browser stores
both values in cookies. The session cookie is HttpOnly. Mutating requests must
send the same CSRF value in the X-CSRF-Token header, which a foreign site cannot
read. SameSite=Lax is a second layer. CORS allows only the configured origins
and never a credentialed wildcard.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api
from app.core.config import get_settings
from app.core.security import CSRF_COOKIE, tokens_match
from app.ml.runtime import load_runtime
from app.services.queues import reconcile_expired_once
from app.services.coordination import deliver_due_reminders_once
from app.services.charging_estimates import deliver_due_once as deliver_charge_estimates_once

logger = logging.getLogger("chargeconnect")
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if settings.initialize_database:
        from app.deployment import migrate_database
        await asyncio.to_thread(migrate_database)
    runtime = load_runtime()
    if settings.initialize_database:
        from app.deployment import initialize_catalogue
        await asyncio.to_thread(initialize_catalogue, runtime)
    stop = asyncio.Event()

    async def reconcile_loop() -> None:
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=settings.reconcile_interval_seconds)
            except TimeoutError:
                try:
                    await asyncio.to_thread(reconcile_expired_once)
                    await asyncio.to_thread(deliver_due_reminders_once)
                    await asyncio.to_thread(deliver_charge_estimates_once)
                except Exception:
                    logger.exception("Offer reconciliation failed")

    task = None
    if settings.environment.lower() != "test":
        task = asyncio.create_task(reconcile_loop())
    try:
        yield
    finally:
        stop.set()
        if task is not None:
            await task


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Elqovanta EV", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Accept", "Content-Type", "X-CSRF-Token"],
    )

    @app.middleware("http")
    async def csrf_guard(request: Request, call_next):
        if request.method not in SAFE_METHODS and request.url.path.startswith("/api/"):
            if not tokens_match(request.cookies.get(CSRF_COOKIE), request.headers.get("x-csrf-token")):
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": {
                            "code": "csrf_failed",
                            "message": "The form token was missing or did not match. Refresh the page and try again.",
                        }
                    },
                )
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        errors = []
        for item in exc.errors():
            location = [str(part) for part in item.get("loc", []) if part != "body"]
            errors.append({"field": ".".join(location), "message": item.get("msg", "Invalid value")})
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "validation_error",
                    "message": "Please check the form and try again.",
                    "errors": errors,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception):
        from fastapi import HTTPException

        if isinstance(exc, HTTPException):
            detail = exc.detail if isinstance(exc.detail, dict) else {"code": "error", "message": str(exc.detail)}
            return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=exc.headers)
        logger.exception("Unhandled server error")
        return JSONResponse(
            status_code=500,
            content={"detail": {"code": "server_error", "message": "Something went wrong on the server."}},
        )

    app.include_router(api, prefix="/api/v1")
    if settings.serve_frontend:
        from app.deployment import mount_frontend
        mount_frontend(app, settings.resolve_backend_path(settings.frontend_path))
    return app


app = create_app()
