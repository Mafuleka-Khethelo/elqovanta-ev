"""Persistent coordination APIs. All model configuration stays examiner-only."""
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_driver, require_manager, require_researcher
from app.core.clock import utcnow
from app.core.errors import fail
from app.db.models import Charger, ChargerReport, ChargingSession, DepartureReport, HistoricalDemonstration, PredictionLog, QueueEntry, Reminder, User
from app.db.session import get_db
from app.ml.prediction import score_scenario
from app.schemas import AssistantOut, DepartureIn, DemonstrationIn, DemonstrationContextOut, ReminderIn, ReportIn, ReportUpdateIn, SwitchQueueIn
from app.services import coordination as service
from app.services.manager import require_assignment
from app.services.participation import lock_charger, lock_user, offers_allowed
from app.services.queues import join_queue, reconcile_charger, waiting_count

router = APIRouter()


@router.get("/sessions/{session_id}/guidance", response_model=AssistantOut, response_model_exclude_none=True)
def session_guidance(session_id: UUID, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    from app.ml.guidance import driver_guidance
    session = db.get(ChargingSession, session_id)
    if session is None or session.user_id != user.id:
        fail(404, "not_found", "Charging session not found.")
    charger = db.get(Charger, session.charger_id)
    return driver_guidance(db, user, charger, port_type=session.port_type, arrival=session.plugged_in_at)


@router.get("/demonstration/context", response_model=DemonstrationContextOut, response_model_exclude_none=True)
def driver_demo_context(user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    context = db.get(HistoricalDemonstration, user.id) if user.is_demonstration else None
    if context is None or context.expires_at <= utcnow():
        return {"active": False}
    charger = db.get(Charger, context.charger_id)
    return {"active": True, "charger_id": charger.id, "charger_name": charger.display_name,
        "historical_arrival_local": context.arrival_local, "timezone": context.timezone_name}


@router.get("/sessions/{session_id}/coordination")
def session_coordination(session_id: UUID, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    session = db.get(ChargingSession, session_id)
    if session is None or session.user_id != user.id:
        fail(404, "not_found", "Charging session not found.")
    charger = db.get(Charger, session.charger_id)
    reminders = db.scalars(select(Reminder).where(Reminder.session_id == session_id).order_by(Reminder.created_at.desc()).limit(5))
    return {"server_time": utcnow(), "timezone": charger.timezone_name,
        "departure": service.departure_payload(db.get(DepartureReport, session_id), utcnow()) if session.unplugged_at is None else None,
        "reminders": [service.reminder_payload(row) for row in reminders], "waiting_count": waiting_count(db, charger.id)}


@router.patch("/sessions/{session_id}/departure")
def departure(session_id: UUID, body: DepartureIn, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    row = service.set_departure(db, user, session_id, body.expected_at, utcnow())
    return {"departure": service.departure_payload(row, utcnow()), "server_time": utcnow()}


@router.post("/sessions/{session_id}/reminders", status_code=201)
def reminder(session_id: UUID, body: ReminderIn, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    return service.reminder_payload(service.schedule_reminder(db, user, session_id, body.due_at, body.idempotency_key, utcnow()))


@router.delete("/reminders/{reminder_id}")
def cancel_reminder(reminder_id: UUID, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    row = service.own_reminder(db, user, reminder_id)
    if row.state == "pending":
        row.state, row.updated_at = "cancelled", utcnow()
    return service.reminder_payload(row)


@router.post("/reminders/{reminder_id}/snooze", status_code=201)
def snooze_reminder(reminder_id: UUID, body: ReminderIn, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    row = service.own_reminder(db, user, reminder_id)
    return service.reminder_payload(service.schedule_reminder(db, user, row.session_id, body.due_at, body.idempotency_key, utcnow()))


@router.get("/chargers/{charger_id}/alternatives")
def alternatives(charger_id: UUID, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    from app.api.v1.chargers import charger_cards
    origin = db.get(Charger, charger_id)
    if origin is None:
        fail(404, "not_found", "Charger not found.")
    cards, _ = charger_cards(db, user)
    own = next((row for row in cards if row["id"] == charger_id), None)
    origin_ports = {port["name"] for port in (own or {}).get("port_types", [])}
    candidates = [row for row in cards if row["id"] != charger_id and row["coordination_enabled"] and row["service_capacity"] and row["app_status"] in ("available", "occupied")]
    for row in candidates:
        shared = origin_ports.intersection(port["name"] for port in row["port_types"])
        row["reasons"] = (["Smaller app queue"] if row["waiting_count"] < (own or {}).get("waiting_count", 0) else ["Another app-enabled charger"]) + (["Same observed port type"] if shared else [])
    candidates.sort(key=lambda row: (row["waiting_count"], "Same observed port type" not in row["reasons"], row["active_session_count"], row["display_name"], str(row["id"])))
    return {"items": candidates[:4], "server_time": utcnow(), "method": "Sorted by app queue size, shared observed port type, connected sessions, then name. This is a rule-based comparison, not a waiting-time prediction or vehicle compatibility guarantee."}


@router.post("/queue/switch")
def switch_queue(body: SwitchQueueIn, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    lock_user(db, user.id)
    replay = db.scalar(select(QueueEntry).where(QueueEntry.user_id == user.id, QueueEntry.idempotency_key == body.idempotency_key))
    if replay is not None:
        if replay.charger_id != body.charger_id:
            fail(409, "duplicate_request", "This request was already used for another charger.")
        return {"state": replay.state, "charger_id": replay.charger_id}
    if body.charger_id == body.expected_charger_id:
        fail(422, "same_charger", "Choose a different charger.")
    # Lock both stable parent rows in the same order, even for opposite switches.
    locked = {key: lock_charger(db, key) for key in sorted({body.expected_charger_id, body.charger_id}, key=str)}
    target = locked[body.charger_id]
    if not offers_allowed(target) or target.app_status not in ("available", "occupied"):
        fail(409, "charger_not_offering", "The alternative is no longer offering app coordination. Your existing place is unchanged.")
    if db.scalar(select(ChargingSession.id).where(ChargingSession.user_id == user.id, ChargingSession.unplugged_at.is_(None))):
        fail(409, "active_session", "Report unplugged before joining another charger.")
    entry = db.scalar(select(QueueEntry).where(QueueEntry.user_id == user.id, QueueEntry.state.in_(("waiting", "offered"))).with_for_update().execution_options(populate_existing=True))
    if entry is None or entry.charger_id != body.expected_charger_id:
        fail(409, "participation_changed", "Your participation changed. Refresh before switching.")
    entry.state, entry.offer_expires_at, entry.updated_at = "left", None, utcnow()
    db.flush()
    replacement = join_queue(db, user, body.charger_id, body.idempotency_key, utcnow(), body.port_type)
    reconcile_charger(db, locked[body.expected_charger_id], utcnow())
    return {"state": replacement.state, "charger_id": replacement.charger_id}


def _reports(db: Session, charger_id: UUID, reporter_id: UUID | None, limit: int, offset: int) -> dict:
    base = select(ChargerReport).where(ChargerReport.charger_id == charger_id)
    if reporter_id is not None:
        base = base.where(ChargerReport.reporter_id == reporter_id)
    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = db.scalars(base.order_by(ChargerReport.created_at.desc()).offset(offset).limit(limit))
    return {"items": [service.report_payload(row) for row in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/chargers/{charger_id}/reports")
def own_reports(charger_id: UUID, limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0), user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    if db.get(Charger, charger_id) is None:
        fail(404, "not_found", "Charger not found.")
    return _reports(db, charger_id, user.id, limit, offset)


@router.post("/chargers/{charger_id}/reports", status_code=201)
def create_report(charger_id: UUID, body: ReportIn, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    return service.report_payload(service.create_report(db, user, charger_id, body.category, body.details, body.idempotency_key, utcnow()))


@router.get("/manager/chargers/{charger_id}/reports")
def manager_reports(charger_id: UUID, limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0), user: User = Depends(require_manager), db: Session = Depends(get_db)) -> dict:
    require_assignment(db, user, charger_id)
    return _reports(db, charger_id, None, limit, offset)


@router.patch("/manager/reports/{report_id}")
def respond_report(report_id: UUID, body: ReportUpdateIn, user: User = Depends(require_manager), db: Session = Depends(get_db)) -> dict:
    return service.report_payload(service.respond_report(db, user, report_id, body.state, body.response, utcnow()))


@router.get("/research/demonstrations")
def demonstration_options(user: User = Depends(require_researcher), db: Session = Depends(get_db)) -> dict:
    del user
    drivers = db.scalars(select(User).where(User.role == "driver", User.is_demonstration.is_(True)).order_by(User.display_name))
    return {"items": [{"id": driver.id, "display_name": driver.display_name, "context": _demo_payload(db.get(HistoricalDemonstration, driver.id))} for driver in drivers]}


def _demo_payload(row: HistoricalDemonstration | None) -> dict | None:
    if row is None:
        return None
    return {"driver_id": row.driver_id, "charger_id": row.charger_id, "arrival_local": row.arrival_local, "port_type": row.port_type, "expires_at": row.expires_at, "selected_at": row.selected_at}


@router.post("/research/demonstrations")
def configure_demonstration(body: DemonstrationIn, user: User = Depends(require_researcher), db: Session = Depends(get_db)) -> dict:
    driver = lock_user(db, body.driver_id)
    if driver.role != "driver" or not driver.is_demonstration:
        fail(403, "demonstration_only", "Choose a provisioned demonstration driver, not a real participant.")
    charger = db.scalar(select(Charger).where(Charger.station_key == body.station_key, Charger.is_historical.is_(True)))
    if charger is None:
        fail(422, "unsupported_charger", "Import the supported historical charger before selecting it for a demonstration.")
    arrival = f"{body.arrival_date.isoformat()}T{body.arrival_time}:00"
    row = db.get(HistoricalDemonstration, driver.id)
    if row and row.charger_id == charger.id and row.port_type == body.port_type and row.arrival_local == arrival and row.expires_at > utcnow():
        return _demo_payload(row)
    result = score_scenario(body.station_key, body.port_type, body.arrival_date, body.arrival_time)
    now = utcnow()
    if row is None:
        row = HistoricalDemonstration(driver_id=driver.id)
        db.add(row)
    row.researcher_id, row.charger_id, row.port_type = user.id, charger.id, body.port_type
    row.arrival_local, row.timezone_name, row.suggest_reminder = result["arrival_local"], result["timezone"], result["warning"]
    row.selected_at, row.expires_at = now, now + timedelta(hours=8)
    db.add(PredictionLog(user_id=user.id, station_key=body.station_key, port_type=body.port_type, arrival_local=result["arrival_local"], timezone_name=result["timezone"], artifact_sha256=result["artifact_sha256"], model_name=result["model_name"], probability=result["probability"], warning=result["warning"], station_sessions_30d=result["station_sessions_30d"], station_long_rate_30d=result["station_long_rate_30d"], created_at=now))
    db.flush()
    return _demo_payload(row)


@router.delete("/research/demonstrations/{driver_id}", status_code=204)
def clear_demonstration(driver_id: UUID, user: User = Depends(require_researcher), db: Session = Depends(get_db)) -> None:
    del user
    lock_user(db, driver_id)
    row = db.get(HistoricalDemonstration, driver_id)
    if row is not None:
        db.delete(row)
