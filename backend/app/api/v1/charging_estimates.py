from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_driver, require_researcher
from app.core.clock import utcnow
from app.core.errors import fail
from app.db.models import ChargeEstimate, Charger, ChargingSession, User
from app.db.session import get_db
from app.schemas import ChargeEstimateIn, EstimateUpdateIn, EstimatePreviewIn, ChargeComparisonIn, AssistantReminderIn, HistoricalAssistantIn
from app.services import charging_estimates as service
from app.services.coordination import own_session

router = APIRouter()


@router.post("/charging-estimates/preview")
def preview(body: EstimatePreviewIn, user: User = Depends(require_driver), db: Session = Depends(get_db)):
    result = service.preview(db, user, body, utcnow())
    return {"estimate": result, "time_budget": service.time_budget(result, body.available_minutes) if body.available_minutes else None, "server_time": utcnow()}


@router.get("/sessions/{session_id}/charge-estimate")
def get_estimate(session_id: UUID, user: User = Depends(require_driver), db: Session = Depends(get_db)):
    session = db.get(ChargingSession, session_id)
    if session is None or session.user_id != user.id:
        fail(404, "not_found", "Session not found.")
    now = utcnow()
    version = int(db.scalar(select(func.max(ChargeEstimate.version)).where(ChargeEstimate.session_id == session_id)) or 0)
    return {"estimate": service.payload(service.active_estimate(db, session_id), now, state=session.state), "version": version,
            "server_time": now, "timezone": db.get(Charger, session.charger_id).timezone_name}


@router.post("/sessions/{session_id}/charge-estimate")
def save_estimate(session_id: UUID, body: EstimateUpdateIn, user: User = Depends(require_driver), db: Session = Depends(get_db)):
    now = utcnow()
    row = service.save(db, user, session_id, body, body.idempotency_key, body.expected_version, now)
    return {"estimate": service.payload(row, now), "server_time": now}


@router.delete("/sessions/{session_id}/charge-estimate", status_code=204)
def clear_estimate(session_id: UUID, version: int = Query(ge=1), user: User = Depends(require_driver), db: Session = Depends(get_db)):
    own_session(db, user, session_id)
    row = service.active_estimate(db, session_id)
    if row and row.version != version:
        fail(409, "estimate_changed", "The estimate changed. Refresh before removing it.")
    if row:
        row.is_active = False
    from app.services.assistant import cancel_assistant_reminder
    cancel_assistant_reminder(db, session_id, utcnow())


@router.get("/chargers/{charger_id}/charging-estimates")
def station_estimates(charger_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if db.get(Charger, charger_id) is None:
        fail(404, "not_found", "Charger not found.")
    now = utcnow()
    return {**service.station_summary(db, charger_id, now), "timezone": db.get(Charger, charger_id).timezone_name}


@router.get("/sessions/{session_id}/assistant-reminder")
def get_assistant_reminder(session_id: UUID, user: User = Depends(require_driver), db: Session = Depends(get_db)):
    from app.services.assistant import get_reminder
    return get_reminder(db, user, session_id)


@router.put("/sessions/{session_id}/assistant-reminder")
def put_assistant_reminder(session_id: UUID, body: AssistantReminderIn, user: User = Depends(require_driver), db: Session = Depends(get_db)):
    from app.services.assistant import set_reminder
    return set_reminder(db, user, session_id, body, utcnow())


@router.post("/charging-estimates/compare")
def compare_chargers(body: ChargeComparisonIn, user: User = Depends(require_driver), db: Session = Depends(get_db)):
    from app.services.assistant import compare
    return compare(db, user, body, utcnow())


@router.post("/research/assistant-preview")
def historical_assistant(body: HistoricalAssistantIn, user: User = Depends(require_researcher), db: Session = Depends(get_db)):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from app.ml.prediction import score_scenario
    if body.plan.vehicle_id or body.plan.charger_id or body.plan.port_type:
        fail(422, "historical_example_only", "Use manual example inputs for this historical demonstration.")
    result = score_scenario(body.station_key, body.port_type, body.arrival_date, body.arrival_time)
    start = datetime.fromisoformat(result["arrival_local"]).replace(tzinfo=ZoneInfo(result["timezone"]))
    estimate = service.preview(db, user, body.plan, start)
    return {"mode": "historical_demonstration", "warning": result["warning"], "arrival_local": result["arrival_local"],
        "timezone": result["timezone"], "estimate": estimate,
        "suggest_return_reminder": result["warning"],
        "remind_at": max(start, estimate["estimated_target_at"]-timedelta(minutes=body.lead_minutes)),
        "notice": "Historical illustration using the unchanged model and hypothetical battery inputs. No live session, reminder or notification is created."}
