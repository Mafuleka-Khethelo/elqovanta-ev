"""Environment configuration.

Paths in settings are relative to the backend directory unless absolute.
Nothing here reads a Windows username or a fixed drive layout.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def backend_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def project_root() -> Path:
    return backend_dir().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(project_root() / ".env", backend_dir() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://chargeconnect:chargeconnect@127.0.0.1:5432/chargeconnect"
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cookie_secure: bool = False
    session_ttl_hours: int = 24 * 14
    artifact_path: str = "artifacts/ev_charger_bundle.joblib"
    environment_manifest_path: str = "artifacts/model_environment.json"
    offer_ttl_seconds: int = 600
    reminder_cooldown_seconds: int = 600
    login_max_failures: int = 5
    login_window_seconds: int = 900
    reconcile_interval_seconds: int = 20
    demo_password: str | None = None
    serve_frontend: bool = False
    frontend_path: str = "../frontend/dist"
    initialize_database: bool = False
    db_pool_size: int = Field(default=5, ge=1, le=20)
    db_max_overflow: int = Field(default=5, ge=0, le=20)

    @field_validator("database_url")
    @classmethod
    def postgres_driver(cls, value: str) -> str:
        # Neon supplies postgresql://; the installed driver is psycopg 3.
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def resolve_backend_path(self, value: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = backend_dir() / path
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
