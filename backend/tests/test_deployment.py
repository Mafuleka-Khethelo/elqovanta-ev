"""Cloud serving must preserve API boundaries, secrets and existing records."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.deployment import initialize_catalogue, migrate_database, mount_frontend


def test_neon_connection_strings_select_psycopg_without_losing_tls_or_escaping():
    for prefix in ("postgres://", "postgresql://", "postgresql+psycopg://"):
        suffix = "user:p%40ss@ep-example.neon.tech/neondb?sslmode=require&channel_binding=require"
        settings = Settings(_env_file=None, database_url=prefix + suffix)
        assert settings.database_url == "postgresql+psycopg://" + suffix


def test_spa_routes_and_assets_preserve_api_and_file_boundaries(tmp_path):
    (tmp_path / "index.html").write_text("<html>Elqovanta EV application</html>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("window.ready=true", encoding="utf-8")
    secret = tmp_path.parent / "outside-secret.txt"
    secret.write_text("never public", encoding="utf-8")
    app = FastAPI()
    @app.get("/api/v1/example")
    def example():
        return {"source": "api"}
    mount_frontend(app, tmp_path)
    with TestClient(app) as http:
        for path in ("/", "/sign-in", "/register", "/app", "/app/chargers/123", "/app/session", "/app/research/predict"):
            response = http.get(path)
            assert response.status_code == 200 and "Elqovanta EV application" in response.text
        assert http.get("/api/v1/example").json() == {"source": "api"}
        assert http.get("/assets/app.js").text == "window.ready=true"
        for path in ("/api", "/api/v1/missing", "/assets/missing.js", "/app/missing.js", "/.env", "/backend/.env", "/%2e%2e/outside-secret.txt"):
            response = http.get(path)
            assert response.status_code == 404, path
            assert "never public" not in response.text and "Elqovanta EV application" not in response.text


def test_missing_frontend_build_fails_clearly(tmp_path):
    with pytest.raises(RuntimeError, match="Build the React frontend"):
        mount_frontend(FastAPI(), tmp_path)


def test_readiness_returns_503_until_database_and_model_are_ready(monkeypatch):
    from app.api.v1 import research
    app = FastAPI()
    app.include_router(research.router)
    with TestClient(app) as http:
        for database, prediction, code in (("unavailable", "ready", 503), ("ok", "unavailable", 503), ("ok", "ready", 200)):
            monkeypatch.setattr(research, "health", lambda: {"database": database, "prediction": prediction})
            assert http.get("/ready").status_code == code


def test_cloud_migration_upgrades_existing_database_without_creating_it(monkeypatch):
    calls = []
    monkeypatch.setattr("alembic.command.upgrade", lambda config, revision: calls.append((config, revision)))
    migrate_database()
    assert len(calls) == 1 and calls[0][1] == "head"
    assert calls[0][0].get_main_option("script_location").endswith("alembic")


def test_cloud_start_preserves_existing_catalogue(db):
    from tests.test_coordination import make_charger
    charger = make_charger(db)
    charger.is_historical = True
    charger.display_name = "Manager's station name"
    db.commit()
    initialize_catalogue(SimpleNamespace(ready=True, bundle=None))
    db.refresh(charger)
    assert charger.display_name == "Manager's station name" and charger.coordination_enabled
