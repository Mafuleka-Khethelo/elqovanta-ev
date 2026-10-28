"""Single-origin frontend serving and additive cloud database initialization."""
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

from app.core.config import backend_dir


def migrate_database() -> None:
    """Use an already provisioned database; never CREATE/DROP a cloud database."""
    from alembic import command
    from alembic.config import Config
    config = Config(str(backend_dir() / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir() / "alembic"))
    command.upgrade(config, "head")


def initialize_catalogue(runtime) -> None:
    from sqlalchemy import select
    from app.db.models import Charger
    from app.db.session import SessionLocal
    from app.services.catalogue import import_history
    if not runtime.ready:
        raise RuntimeError("The saved model must be ready before cloud initialization.")
    with SessionLocal() as db:
        if db.scalar(select(Charger.id).where(Charger.is_historical.is_(True)).limit(1)) is not None:
            return
        import_history(db, runtime.bundle["history"])
        db.commit()


class FrontendFiles(StaticFiles):
    async def get_response(self, path, scope):
        # Missing API paths and assets must stay 404, never become index.html.
        url_path = path.replace("\\", "/")
        first = url_path.strip("/").split("/", 1)[0]
        if first in {"api", "docs", "redoc", "openapi.json"}:
            raise HTTPException(404)
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            segments = url_path.strip("/").split("/")
            browser_route = first in {"", "app", "sign-in", "register", "about", "session-expired", "unavailable"}
            if error.status_code != 404 or not browser_route or any("." in part for part in segments):
                raise
            response = await super().get_response("index.html", scope)
            response.headers["Cache-Control"] = "no-cache"
            return response


def mount_frontend(app: FastAPI, directory: Path) -> None:
    if not (directory / "index.html").is_file():
        raise RuntimeError("Build the React frontend before enabling SERVE_FRONTEND.")
    app.mount("/", FrontendFiles(directory=str(directory), html=True), name="frontend")
