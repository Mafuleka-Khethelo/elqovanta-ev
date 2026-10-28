"""User-chosen departure expectations, durable reminders and private help reports.

All times are operational UTC instants. None of these records is a model input.
Mutation order: acting user, charger, session, then reminder/report records.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import fail
from app.db.models import Charger, ChargerReport, ChargingSession, DepartureReport, ManagerAssignment, Reminder, User
from app.db.session import SessionLocal
from app.services.notifications import notify, short_label
from app.services.participation import lock_charger, lock_user


def future_time(value: datetime, now: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        fail(422, "timezone_required", "Choose a time with its timezone.")
    value = value.astimezone(timezone.utc)
    if not now < value <= now + timedelta(hours=24):
        fail(422, "time_out_of_range", "Choose a future time within the next 24 hours.")
    return value


def own_session(db: Session, user: User, session_id: UUID, *, open_only: bool = True) -> ChargingSession:
    lock_user(db, user.id)
    preview = db.get(ChargingSession, session_id)
    if preview is None or preview.user_id != user.id:
        fail(404, "not_found", "Charging session not found.")
    lock_charger(db, preview.charger_id)
    session = db.scalar(select(ChargingSession).where(ChargingSession.id == session_id).with_for_update().execution_options(populate_existing=True))
    if open_only and session.unplugged_at is not None:
        fail(409, "session_closed", "This session has ended.")
    return session


def set_departure(db: Session, user: User, session_id: UUID, expected_at: datetime | None, now: datetime) -> DepartureReport | None:
    session = own_session(db, user, session_id)
    row = db.get(DepartureReport, session.id)
    if expected_at is None:
        if row is not None:
            row.state, row.reported_at = "retracted", now
        return None
    expected_at = future_time(expected_at, now)
    if row is None:
        row = DepartureReport(session_id=session.id, user_id=user.id, expected_at=expected_at, reported_at=now, state="active")
        db.add(row)
    else:
        row.expected_at, row.reported_at, row.state = expected_at, now, "active"
    db.flush()
    return row


def departure_payload(row: DepartureReport | None, now: datetime) -> dict | None:
    if row is None or row.state != "active" or row.expected_at <= now:
        return None
    return {"expected_at": row.expected_at, "reported_at": row.reported_at}


def public_departures(db: Session, charger_id: UUID, now: datetime) -> list[dict]:
    rows = db.scalars(select(DepartureReport).join(ChargingSession, ChargingSession.id == DepartureReport.session_id).where(
        ChargingSession.charger_id == charger_id, ChargingSession.unplugged_at.is_(None),
        DepartureReport.state == "active", DepartureReport.expected_at > now,
    ).order_by(DepartureReport.expected_at).limit(20))
    # Deliberately omit user IDs, names, session IDs and private contact details.
    return [{"expected_at": row.expected_at, "reported_at": row.reported_at} for row in rows]


def cancel_session_coordination(db: Session, session_id: UUID, now: datetime, *, ended: bool) -> None:
    for reminder in db.scalars(select(Reminder).where(Reminder.session_id == session_id, Reminder.state == "pending").with_for_update()):
        reminder.state, reminder.updated_at = "cancelled", now
    if ended:
        departure = db.get(DepartureReport, session_id)
        if departure is not None:
            departure.state = "ended"


def schedule_reminder(db: Session, user: User, session_id: UUID, due_at: datetime, key: str, now: datetime) -> Reminder:
    session = own_session(db, user, session_id)
    existing = db.scalar(select(Reminder).where(Reminder.user_id == user.id, Reminder.idempotency_key == key))
    if existing is not None:
        if existing.session_id != session_id:
            fail(409, "duplicate_request", "This reminder request belongs to another session.")
        return existing
    if session.state != "finished_plugged":
        fail(409, "reminder_not_applicable", "Report charging finished while still plugged in before setting a return reminder.")
    due_at = future_time(due_at, now)
    cancel_session_coordination(db, session_id, now, ended=False)
    row = Reminder(session_id=session_id, user_id=user.id, due_at=due_at, state="pending", idempotency_key=key, created_at=now, updated_at=now)
    db.add(row)
    db.flush()
    return row


def own_reminder(db: Session, user: User, reminder_id: UUID) -> Reminder:
    preview = db.get(Reminder, reminder_id)
    if preview is None or preview.user_id != user.id:
        fail(404, "not_found", "Reminder not found.")
    own_session(db, user, preview.session_id, open_only=False)
    return db.scalar(select(Reminder).where(Reminder.id == reminder_id).with_for_update().execution_options(populate_existing=True))


def reminder_payload(row: Reminder) -> dict:
    return {"id": row.id, "due_at": row.due_at, "state": row.state, "created_at": row.created_at, "updated_at": row.updated_at}


def deliver_due_reminders_once(now: datetime | None = None) -> int:
    """A restart-safe worker. Notification and delivered state commit together.

    Lock charger/session before claiming a reminder, matching unplug/snooze.
    SKIP LOCKED is for worker claims only; it is never used for FIFO offers.
    """
    now = now or utcnow()
    with SessionLocal() as db:
        candidates = list(db.execute(select(Reminder.id, ChargingSession.charger_id, Reminder.session_id).join(
            ChargingSession, Reminder.session_id == ChargingSession.id
        ).where(Reminder.state == "pending", Reminder.due_at <= now).order_by(Reminder.due_at).limit(100)))
    delivered = 0
    for reminder_id, charger_id, session_id in candidates:
        with SessionLocal() as db:
            lock_charger(db, charger_id)
            session = db.scalar(select(ChargingSession).where(ChargingSession.id == session_id).with_for_update())
            reminder = db.scalar(select(Reminder).where(Reminder.id == reminder_id).with_for_update(skip_locked=True))
            if reminder is None or reminder.state != "pending" or reminder.due_at > now:
                continue
            if session is None or session.state != "finished_plugged" or session.unplugged_at is not None:
                reminder.state = "cancelled"
            else:
                charger = db.get(Charger, charger_id)
                note = notify(db, user_id=reminder.user_id, event_key=f"return-reminder:{reminder.id}",
                    title="Elqovanta EV · Your return reminder", body=f"You asked for a reminder to return to {short_label(charger.display_name)}. Unplug when you are ready, or snooze this reminder in your session.", destination="/app/session")
                reminder.state, reminder.notification_id = "delivered", note.id
                delivered += 1
            reminder.updated_at = now
            db.commit()
    with SessionLocal() as db:
        for row in db.scalars(select(DepartureReport).where(DepartureReport.state == "active", DepartureReport.expected_at <= now).with_for_update(skip_locked=True).limit(100)):
            row.state = "expired"
        db.commit()
    return delivered


def create_report(db: Session, user: User, charger_id: UUID, category: str, details: str, key: str, now: datetime) -> ChargerReport:
    lock_user(db, user.id)
    charger = lock_charger(db, charger_id)
    existing = db.scalar(select(ChargerReport).where(ChargerReport.reporter_id == user.id, ChargerReport.idempotency_key == key))
    if existing is not None:
        if existing.charger_id != charger_id or existing.category != category:
            fail(409, "duplicate_request", "This report request was already used for another issue.")
        return existing
    details = details.strip()
    if len(details) < 3:
        fail(422, "details_required", "Describe the issue briefly.")
    # Serialize through the user lock so repeated reports cannot bypass this bound.
    recent = db.scalars(select(ChargerReport.id).where(ChargerReport.reporter_id == user.id, ChargerReport.created_at > now - timedelta(minutes=10))).all()
    if len(recent) >= 5:
        fail(429, "report_cooldown", "Please wait before sending more help reports.")
    row = ChargerReport(reporter_id=user.id, charger_id=charger_id, category=category, details=details, state="open", idempotency_key=key, created_at=now, updated_at=now)
    db.add(row)
    db.flush()
    for manager_id in db.scalars(select(ManagerAssignment.manager_id).where(ManagerAssignment.charger_id == charger_id)):
        notify(db, user_id=manager_id, event_key=f"help-report:{row.id}:{manager_id}", title="Elqovanta EV · A driver needs help", body=f"A private {category.replace('_', ' ')} report was submitted for {short_label(charger.display_name)}.", destination=f"/app/manage/chargers/{charger_id}")
    return row


def report_payload(row: ChargerReport) -> dict:
    return {"id": row.id, "charger_id": row.charger_id, "category": row.category, "details": row.details, "state": row.state, "manager_response": row.manager_response, "created_at": row.created_at, "updated_at": row.updated_at}


def respond_report(db: Session, manager: User, report_id: UUID, state: str, response: str, now: datetime) -> ChargerReport:
    from app.services.manager import require_assignment
    row = db.get(ChargerReport, report_id)
    if row is None:
        fail(404, "not_found", "Help report not found.")
    require_assignment(db, manager, row.charger_id)
    lock_charger(db, row.charger_id)
    row = db.scalar(select(ChargerReport).where(ChargerReport.id == report_id).with_for_update().execution_options(populate_existing=True))
    response = response.strip()
    if len(response) < 3:
        fail(422, "response_required", "Enter a useful response for the driver.")
    if row.state == state and row.manager_response == response:
        return row
    if row.state == "resolved":
        fail(409, "report_resolved", "This help report is already resolved.")
    row.state, row.manager_response, row.responder_id, row.updated_at = state, response, manager.id, now
    notify(db, user_id=row.reporter_id, event_key=f"help-response:{row.id}:{state}:{now.isoformat()}", title="Elqovanta EV · Help report update", body=response, destination=f"/app/chargers/{row.charger_id}")
    return row
