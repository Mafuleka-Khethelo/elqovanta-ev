"""Operator commands. These are not available as website forms.

Examples, from the backend directory:

    python -m app.cli init-db
    python -m app.cli import-catalogue
    python -m app.cli create-manager --email manager@example.com --name "Alex Manager"
    python -m app.cli assign-charger --email manager@example.com --station-key "EXACT NAME"
    python -m app.cli configure-charger --station-key "EXACT NAME" --capacity 1 --status available
    python -m app.cli seed-demo
"""

import argparse
import os
import re

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine.url import make_url

from app.core.config import backend_dir, get_settings
from app.core.security import hash_password
from app.db.models import Charger, ManagerAssignment, User
from app.db.session import SessionLocal
from app.services.catalogue import import_history


def main() -> None:
    parser = argparse.ArgumentParser(description="Elqovanta EV operator commands")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Create the database if needed and apply migrations")
    sub.add_parser("import-catalogue", help="Import historical chargers from the saved bundle")
    sub.add_parser("list-chargers", help="Print charger keys")

    manager = sub.add_parser("create-manager", help="Create or promote a station manager")
    manager.add_argument("--email", required=True)
    manager.add_argument("--name", required=True)
    manager.add_argument("--password", default=os.environ.get("MANAGER_PASSWORD"))

    researcher = sub.add_parser("create-researcher", help="Provision a separate examiner account")
    researcher.add_argument("--email", required=True)
    researcher.add_argument("--name", required=True)
    researcher.add_argument("--password", default=os.environ.get("RESEARCHER_PASSWORD"))

    assign = sub.add_parser("assign-charger", help="Let a manager administer one charger")
    assign.add_argument("--email", required=True)
    assign.add_argument("--station-key", required=True)

    configure = sub.add_parser("configure-charger", help="Set app capacity and reported status")
    configure.add_argument("--station-key", required=True)
    configure.add_argument("--capacity", required=True, type=int)
    configure.add_argument("--status", default="available")

    sub.add_parser("seed-demo", help="Create labelled demo users and enable one sample charger")
    showcase = sub.add_parser("seed-showcase", help="Create the fictional account walkthrough and local login guide")
    showcase.add_argument("--reset", action="store_true", help="Restore only the owned walkthrough records and relative timers")

    args = parser.parse_args()
    if args.command == "init-db":
        init_db()
    elif args.command == "import-catalogue":
        print(import_catalogue())
    elif args.command == "list-chargers":
        list_chargers()
    elif args.command == "create-manager":
        create_manager(args.email, args.name, args.password)
    elif args.command == "create-researcher":
        create_researcher(args.email, args.name, args.password)
    elif args.command == "assign-charger":
        assign_charger(args.email, args.station_key)
    elif args.command == "configure-charger":
        configure_charger(args.station_key, args.capacity, args.status)
    elif args.command == "seed-demo":
        seed_demo()
    elif args.command == "seed-showcase":
        from app.showcase import seed_showcase
        seed_showcase(reset=args.reset)


def init_db() -> None:
    settings = get_settings()
    url = make_url(settings.database_url)
    database_name = url.database or ""
    if not re.fullmatch(r"[A-Za-z0-9_]+", database_name):
        raise SystemExit("DATABASE_URL database name must contain only letters, numbers and underscores.")
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.execute(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": database_name}).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
            print(f"Created database {database_name}.")
        else:
            print(f"Database {database_name} already exists.")
    admin.dispose()
    from alembic import command
    from alembic.config import Config

    config = Config(str(backend_dir() / "alembic.ini"))
    command.upgrade(config, "head")
    print("Migrations are up to date.")


def import_catalogue():
    from app.ml.runtime import load_runtime

    runtime = load_runtime()
    if not runtime.ready or runtime.bundle is None:
        raise SystemExit(runtime.reason or "The historical model is not available, so the catalogue cannot be imported.")
    with SessionLocal() as db:
        report = import_history(db, runtime.bundle["history"])
        db.commit()
    return report


def list_chargers() -> None:
    with SessionLocal() as db:
        rows = db.scalars(select(Charger).order_by(Charger.station_key)).all()
    for charger in rows:
        print(f"{charger.station_key}\tstatus={charger.app_status}\tcapacity={charger.service_capacity}\tmap={charger.coordinates_on_map}")
    print(f"{len(rows)} chargers")


def create_manager(email: str, name: str, password: str | None) -> None:
    if not password or not 10 <= len(password) <= 128:
        raise SystemExit("Set MANAGER_PASSWORD or pass --password with at least 10 characters.")
    normalised = email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == normalised))
        if user is None:
            user = User(email=normalised, display_name=name.strip(), password_hash=hash_password(password), role="manager")
            db.add(user)
            print(f"Created manager {normalised}.")
        else:
            user.role = "manager"
            user.display_name = name.strip()
            user.password_hash = hash_password(password)
            print(f"Updated {normalised} to a station manager. This command is the only way to grant that role.")
        db.commit()


def create_researcher(email: str, name: str, password: str | None) -> None:
    if not password or len(password) < 10 or len(password) > 128:
        raise SystemExit("Set RESEARCHER_PASSWORD to a phrase of 10–128 characters.")
    from app.services.accounts import normalise_email
    normalised = normalise_email(email)
    if not 2 <= len(name.strip()) <= 80:
        raise SystemExit("Use a display name of 2–80 characters.")
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == normalised))
        if existing is not None:
            raise SystemExit("That email already belongs to an account. Use a separate email for examiner access.")
        db.add(User(email=normalised, display_name=name.strip(), role="researcher", password_hash=hash_password(password)))
        db.commit()
    print(f"Created examiner account {normalised}. It has no station-management or private-message access.")


def assign_charger(email: str, station_key: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email.strip().lower(), User.role == "manager"))
        charger = db.scalar(select(Charger).where(Charger.station_key == station_key))
        if user is None or charger is None:
            raise SystemExit("Manager or exact station key was not found.")
        existing = db.scalar(
            select(ManagerAssignment).where(ManagerAssignment.manager_id == user.id, ManagerAssignment.charger_id == charger.id)
        )
        if existing is None:
            db.add(ManagerAssignment(manager_id=user.id, charger_id=charger.id))
        db.commit()
    print(f"Assigned {email.strip().lower()} to {station_key}.")


def configure_charger(station_key: str, capacity: int, status: str) -> None:
    if not 1 <= capacity <= 20:
        raise SystemExit("Capacity must be between 1 and 20.")
    if status not in {"unknown", "available", "occupied", "offline", "paused"}:
        raise SystemExit("Status must be unknown, available, occupied, offline or paused.")
    from app.core.clock import utcnow

    with SessionLocal() as db:
        charger = db.scalar(select(Charger).where(Charger.station_key == station_key))
        if charger is None:
            raise SystemExit("Exact station key was not found. Run list-chargers to see keys.")
        from app.services.participation import lock_charger, slot_counts
        from app.services.queues import reconcile_charger
        charger = lock_charger(db, charger.id)
        now = utcnow()
        sessions, offers = slot_counts(db, charger.id, now)
        if capacity < sessions + offers:
            raise SystemExit("Capacity cannot be reduced below occupied or offered app slots.")
        charger.service_capacity = capacity
        charger.coordination_enabled = True
        charger.app_status = status
        charger.status_updated_at = utcnow()
        charger.status_source = "Operator configuration"
        charger.status_version += 1
        db.flush()
        reconcile_charger(db, charger, now)
        db.commit()
    print(f"Configured {station_key} with capacity {capacity} and status {status}.")


def seed_demo() -> None:
    settings = get_settings()
    if settings.is_production:
        raise SystemExit("seed-demo does not run when ENVIRONMENT=production.")
    password = settings.demo_password
    if not password or not 10 <= len(password) <= 128:
        raise SystemExit("Set DEMO_PASSWORD in the environment to a phrase of at least 10 characters, then run seed-demo again.")
    from app.ml.runtime import load_runtime

    runtime = load_runtime()
    with SessionLocal() as db:
        if runtime.ready and runtime.bundle is not None and func_count_historical(db) == 0:
            import_history(db, runtime.bundle["history"])
            print("Imported the historical catalogue.")
        users = {
            "demo.driver1@chargeconnect.local": ("Demo Driver One", "driver"),
            "demo.driver2@chargeconnect.local": ("Demo Driver Two", "driver"),
            "demo.manager@chargeconnect.local": ("Demo Manager", "manager"),
            "demo.researcher@elqovanta.local": ("Demo Examiner", "researcher"),
        }
        created = {}
        for email, (name, role) in users.items():
            user = db.scalar(select(User).where(User.email == email))
            if user is not None and not user.is_demonstration:
                raise SystemExit(f"{email} already exists and is not a demonstration account. Seed will not change it.")
            if user is None:
                user = User(email=email, display_name=name, role=role, is_demonstration=True, password_hash=hash_password(password))
                db.add(user)
                db.flush()
            else:
                user.display_name = name
                user.role = role
                user.is_demonstration = True
                user.password_hash = hash_password(password)
            created[email] = user
        manager = created["demo.manager@chargeconnect.local"]
        chargers = list(db.scalars(select(Charger).where(Charger.station_key == "PALO ALTO CA / HAMILTON #2")))
        opened = 0
        for charger in chargers:
            if charger.service_capacity is None:
                charger.service_capacity = 1
                charger.coordination_enabled = True
                opened += 1
            existing = db.scalar(
                select(ManagerAssignment).where(
                    ManagerAssignment.manager_id == manager.id,
                    ManagerAssignment.charger_id == charger.id,
                )
            )
            if existing is None:
                db.add(ManagerAssignment(manager_id=manager.id, charger_id=charger.id))
        print(f"Opened the waiting list on {opened} chargers and assigned them to the demonstration manager.")
        db.commit()
    print("Demonstration accounts:")
    print("  demo.driver1@chargeconnect.local")
    print("  demo.driver2@chargeconnect.local")
    print("  demo.manager@chargeconnect.local")
    print("  demo.researcher@elqovanta.local")
    print("They share DEMO_PASSWORD and are labelled as demonstration accounts.")


def func_count_historical(db) -> int:
    from sqlalchemy import func

    return int(db.scalar(select(func.count()).select_from(Charger).where(Charger.is_historical.is_(True))) or 0)


if __name__ == "__main__":
    main()
