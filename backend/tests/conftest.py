"""PostgreSQL fixtures. Unit tests that do not request `db` stay independent."""

import os

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "postgresql+psycopg://chargeconnect:chargeconnect@127.0.0.1:5432/chargeconnect_test"
os.environ["COOKIE_SECURE"] = "false"

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url

TEST_URL = os.environ["DATABASE_URL"]


def _ensure_database() -> None:
    url = make_url(TEST_URL)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(text("SELECT 1"))
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def database_ready():
    try:
        _ensure_database()
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")
    from app.core.config import get_settings
    from app.db.base import Base
    from app.db import models  # noqa: F401
    from app.db.session import get_engine, reset_engine

    get_settings.cache_clear()
    reset_engine()
    Base.metadata.drop_all(get_engine())
    Base.metadata.create_all(get_engine())
    yield
    reset_engine()


@pytest.fixture
def db(database_ready):
    from app.db.base import Base
    from app.db.session import SessionLocal, get_engine

    _truncate(get_engine(), Base)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        _truncate(get_engine(), Base)


def _truncate(engine, base) -> None:
    names = ", ".join(base.metadata.tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def app_client(database_ready):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def http(app_client, db):
    app_client.cookies.clear()
    yield app_client
    app_client.cookies.clear()


def csrf(client) -> dict[str, str]:
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    return {"X-CSRF-Token": token}


def register(client, email: str, name: str = "Ada Driver", password: str = "correct-horse-battery"):
    response = client.post(
        "/api/v1/auth/register",
        headers=csrf(client),
        json={"email": email, "password": password, "display_name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()["user"]
