"""Station-manager actions.

A manager can change only chargers assigned to them. Reducing capacity below
the slots already taken by sessions or unexpired offers is rejected. Pausing
or switching a charger offline stops new offers without deleting waiting entries.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import get_settings
from app.core.errors import fail
from app.db.models import Charger, ChargerPortType, ChargingSession, ManagerAssignment, Notification, QueueEntry, User
from app.services.notifications import notify, short_label
from app.services.participation import lock_charger, slot_counts
from app.services.queues import reconcile_charger, waiting_count


def validated_timezone(value: str) -> str:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        fail(422, "invalid_timezone", "Choose a recognised charger timezone, such as Africa/Johannesburg or America/Los_Angeles.")
    return value


def assigned_ids(db: Session, manager_id: UUID) -> list[UUID]:
    return list(db.scalars(select(ManagerAssignment.charger_id).where(ManagerAssignment.manager_id == manager_id)))


def require_assignment(db: Session, manager: User, charger_id: UUID) -> Charger:
    if manager.role != "manager":
        fail(403, "managers_only", "Only a station manager can do that.")
    assigned = db.scalar(
        select(ManagerAssignment.id).where(
            ManagerAssignment.manager_id == manager.id,
            ManagerAssignment.charger_id == charger_id,
        )
    )
    if assigned is None:
        fail(404, "not_found", "Charger not found.")
    charger = db.get(Charger, charger_id)
    if charger is None:
        fail(404, "not_found", "Charger not found.")
    return charger


def update_charger(
    db: Session,
    manager: User,
    charger_id: UUID,
    *,
    display_name: str | None,
    app_status: str | None,
    service_capacity: int | None,
    capacity_supplied: bool,
    port_types_to_add: list[str] | None,
    timezone_name: str | None = None,
    port_power_updates: list | None = None,
) -> Charger:
    charger = require_assignment(db, manager, charger_id)
    charger = lock_charger(db, charger.id)
    if timezone_name is not None:
        charger.timezone_name = validated_timezone(timezone_name)
    now = utcnow()
    if display_name is not None:
        cleaned = " ".join(display_name.split())
        if len(cleaned) < 2 or len(cleaned) > 200:
            fail(422, "invalid_name", "Enter a display name between 2 and 200 characters.")
        charger.display_name = cleaned
        charger.display_name_custom = True
    status_changed = False
    if app_status is not None and app_status != charger.app_status:
        charger.app_status = app_status
        charger.status_version += 1
        charger.status_updated_at = now
        charger.status_source = f"Manager: {manager.display_name}"[:200]
        status_changed = True
    if capacity_supplied:
        if service_capacity is None:
            fail(422, "invalid_capacity", "Enter a service capacity of at least 1, or leave it unchanged.")
        if service_capacity < 1 or service_capacity > 20:
            fail(422, "invalid_capacity", "Service capacity must be between 1 and 20.")
        sessions, offers = slot_counts(db, charger.id, now)
        used = sessions + offers
        if service_capacity < used:
            fail(
                409,
                "capacity_too_low",
                f"Capacity cannot be lower than the {used} slot(s) already taken by active sessions or unexpired offers.",
            )
        charger.service_capacity = service_capacity
        charger.coordination_enabled = True
    if port_types_to_add:
        known = {item.name for item in charger.port_types}
        for raw in port_types_to_add:
            name = " ".join(raw.split())
            if not name or len(name) > 120 or name in known:
                continue
            db.add(ChargerPortType(charger_id=charger.id, name=name, origin="manager"))
            known.add(name)
    charger.updated_at = now
    db.flush()
    for specification in port_power_updates or []:
        port = db.scalar(select(ChargerPortType).where(ChargerPortType.charger_id == charger.id, ChargerPortType.name == specification.name))
        if port is None:
            fail(422, "invalid_port", "Choose a listed port before recording power.")
        if (specification.power_kw is None) != (specification.charging_kind is None):
            fail(422, "incomplete_power", "Provide both charging type and power, or clear both.")
        port.power_kw, port.charging_kind = specification.power_kw, specification.charging_kind
        port.power_updated_at = now
    db.flush()
    if status_changed or capacity_supplied:
        reconcile_charger(db, charger, now)
    if status_changed:
        active_users = db.scalars(select(ChargingSession.user_id).where(ChargingSession.charger_id == charger.id, ChargingSession.unplugged_at.is_(None)))
        for driver_id in active_users:
            notify(db, user_id=driver_id, event_key=f"active-status:{charger.id}:{driver_id}:{charger.status_version}", title="Elqovanta EV · App-reported status changed", body=f"The manager reported {short_label(charger.display_name)} as {charger.app_status}. Your app session remains open; contact the manager if you need help.", destination="/app/session")
    return charger


def create_charger(
    db: Session,
    manager: User,
    *,
    display_name: str,
    latitude: float | None,
    longitude: float | None,
    port_types: list[str],
    service_capacity: int | None,
    app_status: str,
    timezone_name: str = "UTC",
) -> Charger:
    if manager.role != "manager":
        fail(403, "managers_only", "Only a station manager can add a charger.")
    timezone_name = validated_timezone(timezone_name)
    cleaned = " ".join(display_name.split())
    if len(cleaned) < 2 or len(cleaned) > 200:
        fail(422, "invalid_name", "Enter a display name between 2 and 200 characters.")
    if db.scalar(select(Charger.id).where(Charger.station_key == cleaned)):
        fail(409, "duplicate_charger", "A charger with that exact name already exists.")
    flag, lat, lon, on_map = _manual_coordinates(latitude, longitude)
    now = utcnow()
    charger = Charger(
        station_key=cleaned,
        display_name=cleaned,
        display_name_custom=False,
        is_historical=False,
        latitude=lat,
        longitude=lon,
        coordinates_on_map=on_map,
        coordinate_flag=flag,
        app_status=app_status,
        status_updated_at=now,
        status_source=f"Manager: {manager.display_name}"[:200],
        timezone_name=timezone_name,
        service_capacity=service_capacity,
        coordination_enabled=service_capacity is not None,
        created_at=now,
        updated_at=now,
    )
    db.add(charger)
    db.flush()
    for raw in port_types:
        name = " ".join(raw.split())
        if name and len(name) <= 120:
            db.add(ChargerPortType(charger_id=charger.id, name=name, origin="manager"))
    db.add(ManagerAssignment(manager_id=manager.id, charger_id=charger.id, created_at=now))
    db.flush()
    return charger


def send_manager_reminder(db: Session, manager: User, charger_id: UUID, driver_id: UUID) -> None:
    charger = require_assignment(db, manager, charger_id)
    entry = db.scalar(
        select(QueueEntry).where(
            QueueEntry.charger_id == charger.id,
            QueueEntry.user_id == driver_id,
            QueueEntry.state.in_(("waiting", "offered")),
        )
    )
    if entry is None:
        fail(404, "not_waiting", "That driver is not currently waiting at this charger.")
    _cooldown(
        db,
        prefix=f"manager-reminder:{charger.id}:{manager.id}:{driver_id}:",
        message="A reminder was already sent to this driver in the last 10 minutes.",
    )
    now = utcnow()
    notify(
        db,
        user_id=driver_id,
        event_key=f"manager-reminder:{charger.id}:{manager.id}:{driver_id}:{int(now.timestamp())}",
        title="Reminder from the station",
        body=(
            f"{manager.display_name} asks you to check your place at {short_label(charger.display_name)}. "
            "This is a coordination reminder, not a penalty."
        ),
        destination="/app/queue",
    )


def send_driver_reminder(db: Session, driver: User, charger_id: UUID) -> None:
    entry = db.scalar(
        select(QueueEntry).where(
            QueueEntry.user_id == driver.id,
            QueueEntry.charger_id == charger_id,
            QueueEntry.state.in_(("waiting", "offered")),
        )
    )
    if entry is None:
        fail(409, "not_waiting", "You can send a reminder only while you are waiting or holding an offer.")
    charger = db.get(Charger, charger_id)
    if charger is None:
        fail(404, "not_found", "Charger not found.")
    _cooldown(
        db,
        prefix=f"driver-reminder:{charger.id}:{driver.id}:",
        message="You already sent a reminder in the last 10 minutes.",
    )
    now = utcnow()
    managers = list(db.scalars(select(ManagerAssignment).where(ManagerAssignment.charger_id == charger.id)))
    if not managers:
        fail(409, "no_manager", "No station manager is assigned to this charger yet.")
    for assignment in managers:
        notify(
            db,
            user_id=assignment.manager_id,
            event_key=f"driver-reminder:{charger.id}:{driver.id}:{assignment.manager_id}:{int(now.timestamp())}",
            title="Waiting driver reminder",
            body=f"{driver.display_name} is still waiting at {short_label(charger.display_name)}.",
            destination=f"/app/manage/chargers/{charger.id}",
        )


def queue_snapshot(db: Session, charger_id: UUID) -> dict[str, int]:
    offered = db.scalar(
        select(func.count()).select_from(QueueEntry).where(QueueEntry.charger_id == charger_id, QueueEntry.state == "offered")
    )
    return {"waiting": waiting_count(db, charger_id), "offered": int(offered or 0)}


def _cooldown(db: Session, prefix: str, message: str) -> None:
    from datetime import timedelta

    settings = get_settings()
    moment = utcnow()
    existing = db.scalar(
        select(Notification.id).where(
            Notification.event_key.startswith(prefix),
            Notification.created_at > moment - timedelta(seconds=settings.reminder_cooldown_seconds),
        )
    )
    if existing is not None:
        fail(429, "reminder_cooldown", message)


def _manual_coordinates(latitude: float | None, longitude: float | None):
    if latitude is None and longitude is None:
        return "missing", None, None, False
    if latitude is None or longitude is None:
        fail(422, "invalid_coordinates", "Enter both latitude and longitude, or leave both empty.")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        fail(422, "invalid_coordinates", "Those coordinates are outside the valid range.")
    if abs(latitude) < 1e-8 and abs(longitude) < 1e-8:
        fail(422, "invalid_coordinates", "Those coordinates are not a usable map location.")
    return "ok", latitude, longitude, True
