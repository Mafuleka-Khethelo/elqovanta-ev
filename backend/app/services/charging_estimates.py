"""Explicit constant-average-power calculations; never an ML or telemetry claim."""
from datetime import datetime, timedelta
from math import ceil
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import fail
from app.db.models import ChargeEstimate, Charger, ChargingSession, Notification, QueueEntry, User, Vehicle
from app.db.session import SessionLocal
from app.schemas import ChargeEstimateIn
from app.services.coordination import own_session
from app.services.notifications import notify, short_label
from app.services.participation import lock_charger

NEAR_MINUTES = 10
ASSUMPTION = "Calculation using an assumed average power reaching the battery, capped by your saved vehicle limit. No live battery connection; slowing, temperature and interruptions can change the time."


def calculate(capacity: float, current: float, target: float, average_kw: float, limit_kw: float | None = None) -> dict:
    if target < current:
        fail(422, "target_below_current", "Choose a target at or above your current battery percentage.")
    effective = min(average_kw, limit_kw) if limit_kw else average_kw
    energy = capacity * (target - current) / 100
    seconds = ceil(energy / effective * 3600)
    if seconds > 7 * 24 * 3600:
        fail(422, "estimate_too_long", "This calculation exceeds seven days. Check the battery capacity and average charging power.")
    return {"energy_needed_kwh": round(energy, 3), "effective_power_kw": effective, "duration_seconds": seconds}


def preview(db: Session, user: User, body: ChargeEstimateIn, now: datetime) -> dict:
    vehicle = None
    if body.vehicle_id:
        vehicle = db.get(Vehicle, body.vehicle_id)
        if vehicle is None or vehicle.user_id != user.id:
            fail(404, "not_found", "Vehicle not found.")
    capacity = (vehicle.battery_capacity_kwh if vehicle and vehicle.battery_capacity_kwh else body.battery_capacity_kwh)
    limit = (vehicle.max_ac_kw if body.charging_kind == "AC" else vehicle.max_dc_kw) if vehicle else None
    calculation = calculate(capacity, body.current_percent, body.target_percent, body.average_power_kw, limit)
    return {**body.model_dump(), **calculation, "battery_capacity_kwh": capacity,
        "vehicle_label": ((vehicle.model_name or vehicle.nickname) if vehicle else body.vehicle_label.strip()),
        "anchor_at": now, "estimated_target_at": now + timedelta(seconds=calculation["duration_seconds"]),
        "assumption": ASSUMPTION, "near_minutes": NEAR_MINUTES, "is_estimate": True}


def active_estimate(db: Session, session_id: UUID) -> ChargeEstimate | None:
    return db.scalar(select(ChargeEstimate).where(ChargeEstimate.session_id == session_id, ChargeEstimate.is_active.is_(True)))


def payload(row: ChargeEstimate | None, now: datetime, *, state: str = "charging") -> dict | None:
    if row is None:
        return None
    elapsed = max(0, (now - row.anchor_at).total_seconds()) if state == "charging" else 0
    estimated_percent = min(row.target_percent, row.current_percent + elapsed * row.effective_power_kw / 3600 / row.battery_capacity_kwh * 100)
    remaining = max(0, ceil((row.estimated_target_at - now).total_seconds()))
    return {"id": row.id, "version": row.version, "vehicle_id": row.vehicle_id, "vehicle_label": row.vehicle_label,
        "battery_capacity_kwh": row.battery_capacity_kwh, "current_percent": row.current_percent,
        "target_percent": row.target_percent, "charging_kind": row.charging_kind, "average_power_kw": row.average_power_kw,
        "effective_power_kw": row.effective_power_kw, "anchor_at": row.anchor_at, "estimated_target_at": row.estimated_target_at,
        "energy_needed_kwh": round(row.battery_capacity_kwh * (row.target_percent - row.current_percent) / 100, 3),
        "duration_seconds": max(0, ceil((row.estimated_target_at - row.anchor_at).total_seconds())),
        "remaining_seconds": remaining, "estimated_percent": round(estimated_percent, 1) if state == "charging" else None,
        "stage": "driver_reported_finished" if state == "finished_plugged" else "estimated_target_time_passed" if remaining == 0 else "approaching_estimated_target" if remaining <= NEAR_MINUTES * 60 else "charging",
        "is_active": row.is_active, "is_estimate": True, "assumption": ASSUMPTION, "near_minutes": NEAR_MINUTES}


def save(db: Session, user: User, session_id: UUID, body: ChargeEstimateIn, key: str, expected_version: int, now: datetime, *, at_start: bool = False) -> ChargeEstimate:
    session = own_session(db, user, session_id)
    previous_request = db.scalar(select(ChargeEstimate).where(ChargeEstimate.session_id == session_id, ChargeEstimate.idempotency_key == key))
    if previous_request is not None:
        return previous_request
    if session.state != "charging":
        fail(409, "not_charging", "An estimate can be updated only while charging is reported as active.")
    latest_version = int(db.scalar(select(func.max(ChargeEstimate.version)).where(ChargeEstimate.session_id == session_id)) or 0)
    if latest_version != expected_version:
        fail(409, "estimate_changed", "This estimate changed in another tab. Refresh before saving your battery reading.")
    anchor = session.plugged_in_at if at_start else now
    calculation = preview(db, user, body, anchor)
    old = active_estimate(db, session_id)
    if old:
        old.is_active = False
        db.flush()
    row = ChargeEstimate(session_id=session.id, vehicle_id=body.vehicle_id,
        vehicle_label=calculation["vehicle_label"], battery_capacity_kwh=calculation["battery_capacity_kwh"],
        current_percent=body.current_percent, target_percent=body.target_percent, charging_kind=body.charging_kind,
        average_power_kw=body.average_power_kw, effective_power_kw=calculation["effective_power_kw"],
        anchor_at=anchor, estimated_target_at=calculation["estimated_target_at"], version=latest_version+1,
        idempotency_key=key, is_active=True, near_notified=False, target_notified=False)
    db.add(row)
    db.flush()
    return row


def station_summary(db: Session, charger_id: UUID, now: datetime) -> dict:
    sessions = list(db.scalars(select(ChargingSession).where(ChargingSession.charger_id == charger_id, ChargingSession.unplugged_at.is_(None))))
    estimates = {r.session_id: r for r in db.scalars(select(ChargeEstimate).join(ChargingSession).where(
        ChargingSession.charger_id == charger_id, ChargingSession.unplugged_at.is_(None), ChargeEstimate.is_active.is_(True)))}
    items = []
    unknown = 0
    for session in sessions:
        row = estimates.get(session.id)
        if session.state == "finished_plugged":
            items.append({"stage": "driver_reported_finished", "estimated_target_at": None, "is_estimate": False})
        elif session.state == "charging" and row:
            items.append({"stage": payload(row, now)["stage"], "estimated_target_at": row.estimated_target_at, "is_estimate": True})
        else:
            unknown += 1
    # No driver, session, vehicle, capacity or battery-percentage identifiers.
    items.sort(key=lambda item: (item["estimated_target_at"] is not None, item["estimated_target_at"] or now))
    return {"items": items, "connected_count": len(sessions), "unestimated_count": unknown,
        "server_time": now, "notice": "Charging completion does not free a bay. Offers follow a reported unplug, not this estimate."}


def _waiting_ids(db: Session, charger_id: UUID):
    return set(db.scalars(select(QueueEntry.user_id).where(QueueEntry.charger_id == charger_id, QueueEntry.state.in_(("waiting", "offered")))))


def report_finished(db: Session, session: ChargingSession, now: datetime):
    charger = db.get(Charger, session.charger_id)
    for user_id in _waiting_ids(db, session.charger_id):
        notify(db, user_id=user_id, event_key=f"charging-finished:{session.id}:{user_id}",
            title="A driver reported charging finished", body=f"A driver at {short_label(charger.display_name)} reported charging finished but is still connected. Wait for your app offer after they unplug.", destination="/app/queue")


def deliver_due_once(now: datetime | None = None) -> int:
    now = now or utcnow()
    with SessionLocal() as db:
        candidates = list(db.execute(select(ChargeEstimate.id, ChargingSession.charger_id, ChargingSession.id).join(ChargingSession).where(
            ChargeEstimate.is_active.is_(True), ChargingSession.state == "charging", ChargingSession.unplugged_at.is_(None),
            ChargeEstimate.estimated_target_at <= now + timedelta(minutes=NEAR_MINUTES),
            or_(and_(ChargeEstimate.estimated_target_at <= now, ChargeEstimate.target_notified.is_(False)),
                and_(ChargeEstimate.estimated_target_at > now, ChargeEstimate.near_notified.is_(False)))
        ).order_by(ChargeEstimate.estimated_target_at).limit(100)))
    delivered = 0
    for estimate_id, charger_id, session_id in candidates:
        with SessionLocal() as db:
            charger = lock_charger(db, charger_id)
            session = db.scalar(select(ChargingSession).where(ChargingSession.id == session_id).with_for_update())
            row = db.scalar(select(ChargeEstimate).where(ChargeEstimate.id == estimate_id).with_for_update(skip_locked=True))
            if row is None or not row.is_active or session.state != "charging" or session.unplugged_at is not None:
                continue
            due = row.estimated_target_at <= now
            if (due and row.target_notified) or (not due and row.near_notified):
                continue
            phase = "target" if due else "near"
            time_label = row.estimated_target_at.astimezone(ZoneInfo(charger.timezone_name)).strftime("%d %b, %H:%M %Z")
            recipients = _waiting_ids(db, charger_id) | {session.user_id}
            for user_id in recipients:
                prefix = f"charge-{phase}:{session.id}:"
                # A revised reading must not flood people with the same alert.
                recent = db.scalar(select(Notification.id).where(Notification.user_id == user_id,
                    Notification.event_key.like(prefix+"%"), Notification.created_at > now-timedelta(minutes=10)).limit(1))
                if recent:
                    continue
                owner = user_id == session.user_id
                title = "Estimated target time reached" if due else "Approaching estimated charging target"
                body = (f"Your estimated target time at {short_label(charger.display_name)} is {time_label}. Check your car; confirm charging finished or update your battery reading. This is not a live full-battery detection." if owner else
                    f"A session at {short_label(charger.display_name)} has an estimated charging target around {time_label}. Completion is not confirmed; the driver must unplug before the next app offer.")
                notify(db, user_id=user_id, event_key=f"{prefix}{row.id}:{user_id}", title=title, body=body, destination="/app/session" if owner else "/app/queue")
                delivered += 1
            row.near_notified = True
            if due:
                row.target_notified = True
            db.commit()
    return delivered
