"""Driver-reported charging sessions.

These are reports by participating users, not readings from charger hardware.
Durations are derived from server timestamps. The browser cannot submit totals.

A session starts when the driver reports plugging in and beginning to charge.
Pause and resume close and open charging intervals. "Finished charging" means
the driver is still plugged in. Unplug closes the session.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import fail
from app.db.models import (
    Charger,
    ChargingInterval,
    ChargingSession,
    ManagerAssignment,
    QueueEntry,
    SessionEvent,
    User,
)
from app.services.durations import DurationError, summarise_seconds
from app.services.participation import (
    ensure_free_to_participate,
    lock_charger,
    lock_user,
    offers_allowed,
    slot_counts,
)


def session_seconds(session: ChargingSession, intervals: list[ChargingInterval], now: datetime) -> dict[str, int]:
    try:
        connected, charging, noncharging = summarise_seconds(
            session.plugged_in_at,
            session.unplugged_at,
            [(item.started_at, item.ended_at) for item in intervals],
            now,
        )
    except DurationError as exc:
        fail(500, "duration_error", str(exc))
    return {
        "connected_seconds": connected,
        "charging_seconds": charging,
        "noncharging_seconds": noncharging,
    }


def refresh_reported_status(db: Session, charger: Charger, source: str, now: datetime) -> None:
    """Move only between available and occupied.

    Paused, offline and unknown stay as a manager left them. This update is
    still an app report: it is not a hardware sensor.
    """
    if charger.app_status not in ("available", "occupied"):
        return
    active = db.scalar(
        select(func.count())
        .select_from(ChargingSession)
        .where(ChargingSession.charger_id == charger.id, ChargingSession.unplugged_at.is_(None))
    )
    active = int(active or 0)
    capacity = charger.service_capacity or 0
    new_status = "occupied" if active > 0 and capacity > 0 and active >= capacity else "available"
    if new_status == charger.app_status:
        return
    charger.app_status = new_status
    charger.status_updated_at = now
    charger.status_source = source[:200]
    charger.updated_at = now


def _intervals(db: Session, session_id: UUID) -> list[ChargingInterval]:
    return list(
        db.scalars(
            select(ChargingInterval)
            .where(ChargingInterval.session_id == session_id)
            .order_by(ChargingInterval.started_at)
            .with_for_update()
        )
    )


def _open_interval(intervals: list[ChargingInterval]) -> ChargingInterval | None:
    return next((item for item in intervals if item.ended_at is None), None)


def _add_event(
    db: Session,
    session: ChargingSession,
    actor_id: UUID | None,
    event_type: str,
    now: datetime,
    idempotency_key: str | None,
    reason: str | None = None,
) -> None:
    db.add(
        SessionEvent(
            session_id=session.id,
            actor_user_id=actor_id,
            event_type=event_type,
            reason=reason,
            idempotency_key=idempotency_key,
            created_at=now,
        )
    )


def create_charging_session(
    db: Session,
    *,
    user: User,
    charger: Charger,
    idempotency_key: str,
    now: datetime,
    actor_id: UUID,
    source_label: str,
    port_type: str | None = None,
) -> ChargingSession:
    session = ChargingSession(
        user_id=user.id,
        charger_id=charger.id,
        state="charging",
        port_type=port_type,
        plugged_in_at=now,
        idempotency_key=idempotency_key,
        is_demonstration=user.is_demonstration,
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.flush()
    db.add(ChargingInterval(session_id=session.id, started_at=now))
    _add_event(db, session, actor_id, "session_started", now, idempotency_key)
    db.flush()
    refresh_reported_status(db, charger, source_label, now)
    return session


def _replay_event(db: Session, session_id: UUID, idempotency_key: str | None) -> bool:
    if not idempotency_key:
        return False
    existing = db.scalar(
        select(SessionEvent.id).where(
            SessionEvent.session_id == session_id,
            SessionEvent.idempotency_key == idempotency_key,
        )
    )
    return existing is not None


def apply_action(
    db: Session,
    session: ChargingSession,
    *,
    action: str,
    actor_id: UUID | None,
    now: datetime,
    idempotency_key: str | None,
    reason: str | None = None,
) -> ChargingSession:
    if _replay_event(db, session.id, idempotency_key):
        return session
    if session.state == "unplugged":
        fail(409, "session_closed", "This session is already unplugged.")
    intervals = _intervals(db, session.id)

    if action == "pause":
        if session.state != "charging":
            fail(409, "invalid_transition", "Pause is only available while charging is reported as active.")
        open_interval = _open_interval(intervals)
        if open_interval is None:
            fail(500, "duration_error", "The charging interval could not be found.")
        open_interval.ended_at = now
        session.state = "paused"
        event_type = "charging_paused"
    elif action == "resume":
        if session.state not in ("paused", "finished_plugged"):
            fail(409, "invalid_transition", "Resume is available after pausing or reporting charging finished.")
        if _open_interval(intervals) is not None:
            fail(409, "invalid_transition", "Charging is already recorded as active.")
        db.add(ChargingInterval(session_id=session.id, started_at=now))
        session.state = "charging"
        event_type = "charging_resumed"
    elif action == "finish":
        if session.state == "charging":
            open_interval = _open_interval(intervals)
            if open_interval is None:
                fail(500, "duration_error", "The charging interval could not be found.")
            open_interval.ended_at = now
        elif session.state != "paused":
            fail(409, "invalid_transition", "Charging has already been reported as finished.")
        session.state = "finished_plugged"
        event_type = "charging_finished"
    elif action in ("unplug", "manager_close"):
        if action == "manager_close" and (not reason or len(reason.strip()) < 5):
            fail(422, "reason_required", "Enter a short reason for closing this session.")
        if session.state == "charging":
            open_interval = _open_interval(intervals)
            if open_interval is None:
                fail(500, "duration_error", "The charging interval could not be found.")
            open_interval.ended_at = now
        session.state = "unplugged"
        session.unplugged_at = now
        event_type = "manager_close" if action == "manager_close" else "unplugged"
    else:
        fail(400, "unknown_action", "That session action is not recognised.")

    if action in ("resume", "unplug", "manager_close"):
        from app.services.coordination import cancel_session_coordination
        cancel_session_coordination(db, session.id, now, ended=action in ("unplug", "manager_close"))
    session.updated_at = now
    _add_event(db, session, actor_id, event_type, now, idempotency_key, reason.strip() if reason else None)
    db.flush()
    # Reject a sequence that produced a negative or overlapping duration.
    session_seconds(session, _intervals(db, session.id), now)
    return session


def _own_open_session(db: Session, user_id: UUID, session_id: UUID) -> ChargingSession:
    session = db.scalar(
        select(ChargingSession)
        .where(ChargingSession.id == session_id, ChargingSession.user_id == user_id)
        .with_for_update()
    )
    if session is None:
        fail(404, "not_found", "Charging session not found.")
    return session


def _release_if_closed(db: Session, session: ChargingSession, actor_label: str, now: datetime) -> None:
    if session.unplugged_at is None:
        return
    charger = lock_charger(db, session.charger_id)
    refresh_reported_status(db, charger, actor_label, now)
    from app.services.queues import reconcile_charger

    reconcile_charger(db, charger, now)


def direct_start(db: Session, user: User, charger_id: UUID, idempotency_key: str, now: datetime, port_type: str | None = None) -> ChargingSession:
    lock_user(db, user.id)
    existing = db.scalar(
        select(ChargingSession).where(
            ChargingSession.user_id == user.id,
            ChargingSession.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing
    ensure_free_to_participate(db, user.id)
    charger = lock_charger(db, charger_id)
    from app.services.ports import selected_port
    port_type = selected_port(db, charger_id, port_type)
    if not charger.coordination_enabled or not charger.service_capacity:
        fail(409, "coordination_disabled", "App coordination is not configured for this charger yet.")
    if charger.app_status in ("paused", "offline"):
        fail(409, "charger_not_offering", f"This charger is {charger.app_status}, so a new session cannot start.")
    from app.services.queues import reconcile_charger

    reconcile_charger(db, charger, now)
    waiting = db.scalar(
        select(func.count())
        .select_from(QueueEntry)
        .where(QueueEntry.charger_id == charger.id, QueueEntry.state.in_(("waiting", "offered")))
    )
    if int(waiting or 0) > 0:
        fail(
            409,
            "queue_not_empty",
            "Other drivers are already waiting. Join the waiting list instead of starting immediately.",
        )
    sessions, offers = slot_counts(db, charger.id, now)
    if sessions + offers >= charger.service_capacity:
        fail(409, "no_slot", "Every configured app slot is already taken.")
    if not offers_allowed(charger):
        fail(409, "charger_not_offering", "This charger is not offering app slots right now.")
    return create_charging_session(
        db,
        user=user,
        charger=charger,
        idempotency_key=idempotency_key,
        now=now,
        actor_id=user.id,
        source_label="Driver session report",
        port_type=port_type,
    )


def driver_action(
    db: Session,
    user: User,
    session_id: UUID,
    action: str,
    idempotency_key: str,
    now: datetime,
) -> ChargingSession:
    preview = db.get(ChargingSession, session_id)
    if preview is None or preview.user_id != user.id:
        fail(404, "not_found", "Charging session not found.")
    lock_user(db, user.id)
    lock_charger(db, preview.charger_id)
    session = _own_open_session(db, user.id, session_id)
    apply_action(
        db,
        session,
        action=action,
        actor_id=user.id,
        now=now,
        idempotency_key=idempotency_key,
    )
    _release_if_closed(db, session, "Driver session report", now)
    return session


def manager_close(
    db: Session,
    manager: User,
    charger_id: UUID,
    session_id: UUID,
    reason: str,
    idempotency_key: str,
    now: datetime,
) -> ChargingSession:
    assigned = db.scalar(
        select(ManagerAssignment.id).where(
            ManagerAssignment.manager_id == manager.id,
            ManagerAssignment.charger_id == charger_id,
        )
    )
    if assigned is None:
        fail(404, "not_found", "Charger not found.")
    lock_charger(db, charger_id)
    session = db.scalar(
        select(ChargingSession)
        .where(ChargingSession.id == session_id, ChargingSession.charger_id == charger_id)
        .with_for_update()
    )
    if session is None:
        fail(404, "not_found", "Charging session not found.")
    apply_action(
        db,
        session,
        action="manager_close",
        actor_id=manager.id,
        now=now,
        idempotency_key=idempotency_key,
        reason=reason,
    )
    _release_if_closed(db, session, f"Manager: {manager.display_name}", now)
    from app.services.notifications import notify
    notify(db, user_id=session.user_id, event_key=f"manager-close:{session.id}:{idempotency_key}", title="Elqovanta EV · Your app session was closed", body=f"An assigned station manager closed your app session. Reason: {reason.strip()}", destination="/app/history")
    return session


def report_still_charging(db: Session, user: User, session_id: UUID, idempotency_key: str, now: datetime) -> None:
    """A driver can say they are still charging. A model warning never removes them."""
    from datetime import timedelta

    from app.services.notifications import notify, short_label

    lock_user(db, user.id)
    session = _own_open_session(db, user.id, session_id)
    if session.state != "charging":
        fail(409, "invalid_transition", "The still-charging report is available while charging is active.")
    if _replay_event(db, session.id, idempotency_key):
        return
    cutoff = now - timedelta(seconds=600)
    recent = db.scalar(
        select(SessionEvent.id).where(
            SessionEvent.session_id == session.id,
            SessionEvent.event_type == "still_charging",
            SessionEvent.created_at > cutoff,
        )
    )
    if recent is not None:
        fail(429, "reminder_cooldown", "A still-charging report was already sent in the last 10 minutes.")
    _add_event(db, session, user.id, "still_charging", now, idempotency_key)
    charger = db.get(Charger, session.charger_id)
    label = short_label(charger.display_name if charger else "the charger")
    managers = db.scalars(select(ManagerAssignment).where(ManagerAssignment.charger_id == session.charger_id))
    for assignment in managers:
        notify(
            db,
            user_id=assignment.manager_id,
            event_key=f"still-charging:{session.id}:{idempotency_key}:{assignment.manager_id}",
            title="Driver is still charging",
            body=f"{user.display_name} reports they are still charging at {label}. This does not change the queue.",
            destination=f"/manager/chargers/{session.charger_id}",
        )

