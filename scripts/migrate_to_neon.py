"""Copy local app records to a new, empty Neon DB. Credentials are never printed."""
import getpass
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from app.core.config import Settings, get_settings
from app.database_transfer import copy_records


def main():
    target_value = getpass.getpass("New Neon database URL (hidden): ")
    target = make_url(Settings(_env_file=None, database_url=target_value).database_url)
    if not target.host or not target.host.endswith((".neon.tech", ".neon.build")):
        raise ValueError("The destination must be your new Neon database.")
    source_value = get_settings().database_url
    source = make_url(source_value)
    if source.host not in {"127.0.0.1", "localhost"}:
        raise ValueError("The source must be the local presentation database.")
    # Upgrade the already-provisioned destination only; no CREATE DATABASE.
    os.environ["DATABASE_URL"] = target.render_as_string(hide_password=False)
    get_settings.cache_clear()
    from app.deployment import migrate_database
    migrate_database()
    source_engine = create_engine(source_value, pool_pre_ping=True, connect_args={"connect_timeout": 10})
    target_engine = create_engine(target, pool_pre_ping=True, connect_args={"connect_timeout": 15})
    try:
        counts = copy_records(source_engine, target_engine)
    finally:
        source_engine.dispose()
        target_engine.dispose()
    print(json.dumps({"copied": counts, "source_unchanged": True, "login_sessions_copied": False}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Connection strings/passwords must not enter shell logs.
        print(f"Transfer stopped ({type(error).__name__}). No source records were changed.", file=sys.stderr)
        raise SystemExit(1)
