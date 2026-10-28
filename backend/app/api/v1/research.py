"""Historical research, manager tools, health and the public summary.

Prediction uses the frozen bundle only. Application sessions are never added
to that history and are never sent to the pipeline as inputs.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_manager, require_researcher
from app.core.clock import utcnow
from app.core.errors import fail
from app.db.models import (
    Charger,
    ChargingSession,
    ManagerAssignment,
    PredictionLog,
    QueueEntry,
    SessionEvent,
    User,
)
from app.db.session import SessionLocal, get_db
from app.ml.prediction import score_scenario
from app.ml.insights import summarise_history
from app.ml.runtime import LIMITATIONS, get_runtime
from app.schemas import ChargerCreateIn, ChargerUpdateIn, CloseSessionIn, PredictIn, RemindIn
from app.services.manager import (
    assigned_ids,
    create_charger,
    queue_snapshot,
    require_assignment,
    send_manager_reminder,
    update_charger,
)
from app.services.sessions import manager_close, session_seconds
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
def health() -> dict:
    database = "unavailable"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"
    runtime = get_runtime()
    return {
        "status": "ok" if database == "ok" else "degraded",
        "database": database,
        "prediction": "ready" if runtime.ready else "unavailable",
        "prediction_reason": None if runtime.ready else runtime.reason,
    }


@router.get("/ready")
def ready() -> JSONResponse:
    result = health()
    available = result["database"] == "ok" and result["prediction"] == "ready"
    return JSONResponse(status_code=200 if available else 503,
        content={"status": "ready" if available else "starting", "database": result["database"], "prediction": result["prediction"]})


@router.get("/public/summary")
def public_summary() -> dict:
    try:
        with SessionLocal() as db:
            historical = int(
                db.scalar(select(func.count()).select_from(Charger).where(Charger.is_historical.is_(True))) or 0
            )
            enabled = int(
                db.scalar(select(func.count()).select_from(Charger).where(Charger.coordination_enabled.is_(True))) or 0
            )
    except Exception:
        return {"catalogue_imported": False, "historical_chargers": None, "coordination_enabled": None}
    return {
        "catalogue_imported": historical > 0,
        "historical_chargers": historical,
        "coordination_enabled": enabled,
    }


@router.get("/research/model")
def model_card(manager: User = Depends(require_researcher)) -> dict:
    del manager
    runtime = get_runtime()
    if not runtime.ready or runtime.bundle is None:
        return {"ready": False, "reason": runtime.reason, "limitations": LIMITATIONS}
    bundle = runtime.bundle
    return {
        "ready": True,
        "reason": None,
        "model_name": bundle["model_name"],
        "schema_version": bundle["schema_version"],
        "artifact_sha256": runtime.artifact_sha256,
        "warning_cutoff": bundle["warning_cutoff"],
        "noncharging_threshold_minutes": bundle["noncharging_threshold_minutes"],
        "history_window_days": bundle["history_window_days"],
        "exclude_arrival_day": bundle["exclude_arrival_day"],
        "timezone": bundle["timezone"],
        "validation_year": bundle["validation_year"],
        "test_year": bundle["test_year"],
        "feature_columns": list(bundle["feature_columns"]),
        "classifier_params": runtime.classifier_params,
        "metrics_match_reference": runtime.metrics_match_reference,
        "metrics_table": runtime.metrics_table,
        "confusion_matrix": runtime.confusion_matrix,
        "confusion_labels": [0, 1],
        "package_versions": runtime.package_versions,
        "limitations": LIMITATIONS,
        "plain_language": (
            "About 14 out of every 100 warnings in the 2020 test were correct, and the model "
            "detected about 70 out of every 100 actual long noncharging sessions. "
            "Most warnings were false alarms. Always warning did only a little worse, so the improvement is modest."
            if runtime.metrics_match_reference
            else None
        ),
    }


@router.get("/research/options")
def research_options(user: User = Depends(require_researcher)) -> dict:
    """Exact charger and port pairs the frozen history can score.

    This list comes from the saved bundle, not from the live application
    database, and it is not limited to the paginated charger search.
    """
    del user
    runtime = get_runtime()
    if not runtime.ready or runtime.bundle is None:
        fail(503, "prediction_unavailable", runtime.reason or "Historical research data is unavailable.")
    grouped: dict[str, set[str]] = {}
    for station, port in runtime.supported_pairs:
        grouped.setdefault(station, set()).add(port)
    return {
        "items": [
            {"station_key": station, "port_types": sorted(ports)}
            for station, ports in sorted(grouped.items())
        ],
        "timezone": runtime.bundle["timezone"],
        "arrival_year": int(runtime.bundle["test_year"]),
    }


@router.get("/research/insights")
def insights(
    station_key: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(require_researcher),
) -> dict:
    del user
    if (start_date is None) ^ (end_date is None):
        fail(422, "date_range", "Provide both a start date and an end date, or leave both empty.")
    if start_date is not None and end_date is not None and end_date < start_date:
        fail(422, "date_range", "The end date must be on or after the start date.")
    runtime = get_runtime()
    if not runtime.ready or runtime.bundle is None:
        fail(503, "prediction_unavailable", runtime.reason or "Historical research data is unavailable.")
    summary = summarise_history(
        runtime.bundle["history"],
        station_key=station_key,
        start_date=start_date,
        end_date=end_date,
    )
    summary.update(
        {
            "source": "Frozen Palo Alto charging history supplied with the saved model.",
            "time_basis": "Historical local start time, already stored as Palo Alto wall-clock time.",
            "station_key": station_key,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        }
    )
    return summary


@router.post("/research/predict")
def predict(body: PredictIn, user: User = Depends(require_researcher), db: Session = Depends(get_db)) -> dict:
    result = score_scenario(body.station_key, body.port_type, body.arrival_date, body.arrival_time)
    db.add(
        PredictionLog(
            user_id=user.id,
            station_key=body.station_key,
            port_type=body.port_type,
            arrival_local=result["arrival_local"],
            timezone_name=result["timezone"],
            artifact_sha256=result["artifact_sha256"] or "",
            model_name=result["model_name"],
            probability=result["probability"],
            warning=result["warning"],
            station_sessions_30d=result["station_sessions_30d"],
            station_long_rate_30d=result["station_long_rate_30d"],
            created_at=utcnow(),
        )
    )
    return result


@router.get("/manager/overview")
def manager_overview(manager: User = Depends(require_manager), db: Session = Depends(get_db)) -> dict:
    ids = assigned_ids(db, manager.id)
    if not ids:
        return {"chargers": [], "active_sessions": 0, "waiting_participants": 0, "completed_sessions": 0, "reported_noncharging_minutes": 0, "has_activity": False, "activity": []}
    chargers = list(db.scalars(select(Charger).where(Charger.id.in_(ids)).options(selectinload(Charger.port_types)).order_by(Charger.display_name)))
    cards = []
    active_total = waiting_total = completed_total = 0
    noncharging_seconds = 0
    for charger in chargers:
        active = int(
            db.scalar(
                select(func.count()).select_from(ChargingSession).where(ChargingSession.charger_id == charger.id, ChargingSession.unplugged_at.is_(None))
            )
            or 0
        )
        completed_rows = list(
            db.scalars(
                select(ChargingSession)
                .where(ChargingSession.charger_id == charger.id, ChargingSession.unplugged_at.is_not(None))
                .options(selectinload(ChargingSession.intervals))
            )
        )
        charger_noncharging = 0
        for session in completed_rows:
            charger_noncharging += session_seconds(session, list(session.intervals), utcnow())["noncharging_seconds"]
        snapshot = queue_snapshot(db, charger.id)
        active_total += active
        waiting_total += snapshot["waiting"]
        completed_total += len(completed_rows)
        noncharging_seconds += charger_noncharging
        cards.append(
            {
                "id": charger.id,
                "display_name": charger.display_name,
                "station_key": charger.station_key,
                "is_historical": charger.is_historical,
                "app_status": charger.app_status,
                "status_updated_at": charger.status_updated_at,
                "status_source": charger.status_source,
                "service_capacity": charger.service_capacity,
                "coordination_enabled": charger.coordination_enabled,
                "active_sessions": active,
                "waiting": snapshot["waiting"],
                "offered": snapshot["offered"],
                "completed_sessions": len(completed_rows),
                "reported_noncharging_minutes": round(charger_noncharging / 60, 1),
            }
        )
    activity_rows = db.execute(
        select(SessionEvent, ChargingSession, Charger.display_name, User.display_name)
        .join(ChargingSession, SessionEvent.session_id == ChargingSession.id)
        .join(Charger, ChargingSession.charger_id == Charger.id)
        .outerjoin(User, SessionEvent.actor_user_id == User.id)
        .where(ChargingSession.charger_id.in_(ids))
        .order_by(SessionEvent.created_at.desc())
        .limit(20)
    ).all()
    return {
        "chargers": cards,
        "active_sessions": active_total,
        "waiting_participants": waiting_total,
        "completed_sessions": completed_total,
        "reported_noncharging_minutes": round(noncharging_seconds / 60, 1),
        "has_activity": (active_total + waiting_total + completed_total) > 0,
        "activity": [
            {
                "event_type": event.event_type,
                "reason": event.reason,
                "created_at": event.created_at,
                "charger_name": charger_name,
                "actor_name": actor_name,
                "is_demonstration": session.is_demonstration,
            }
            for event, session, charger_name, actor_name in activity_rows
        ],
    }


@router.post("/manager/chargers", status_code=201)
def post_charger(body: ChargerCreateIn, manager: User = Depends(require_manager), db: Session = Depends(get_db)) -> dict:
    charger = create_charger(
        db,
        manager,
        display_name=body.display_name,
        latitude=body.latitude,
        longitude=body.longitude,
        port_types=body.port_types,
        service_capacity=body.service_capacity,
        app_status=body.app_status,
        timezone_name=body.timezone,
    )
    return {"id": charger.id, "station_key": charger.station_key}


@router.get("/manager/chargers/{charger_id}")
def manager_charger(charger_id: UUID, manager: User = Depends(require_manager), db: Session = Depends(get_db)) -> dict:
    charger = require_assignment(db, manager, charger_id)
    sessions = list(
        db.scalars(
            select(ChargingSession)
            .where(ChargingSession.charger_id == charger.id, ChargingSession.unplugged_at.is_(None))
            .options(selectinload(ChargingSession.intervals))
        )
    )
    queue_rows = list(
        db.scalars(
            select(QueueEntry)
            .where(QueueEntry.charger_id == charger.id, QueueEntry.state.in_(("waiting", "offered")))
            .order_by(QueueEntry.joined_at)
        )
    )
    user_ids = {session.user_id for session in sessions} | {row.user_id for row in queue_rows}
    names = {person.id: person.display_name for person in db.scalars(select(User).where(User.id.in_(user_ids)))} if user_ids else {}
    now = utcnow()
    return {
        "id": charger.id,
        "station_key": charger.station_key,
        "timezone": charger.timezone_name,
        "display_name": charger.display_name,
        "is_historical": charger.is_historical,
        "app_status": charger.app_status,
        "status_updated_at": charger.status_updated_at,
        "status_source": charger.status_source,
        "service_capacity": charger.service_capacity,
        "coordination_enabled": charger.coordination_enabled,
        "coordinate_flag": charger.coordinate_flag,
        "port_types": [{"name": item.name, "origin": item.origin} for item in charger.port_types],
        "sessions": [
            {
                "id": session.id,
                "driver_name": names.get(session.user_id, "Driver"),
                "state": session.state,
                "is_demonstration": session.is_demonstration,
                "plugged_in_at": session.plugged_in_at,
                **session_seconds(session, list(session.intervals), now),
            }
            for session in sessions
        ],
        "queue": [
            {
                "user_id": row.user_id,
                "driver_name": names.get(row.user_id, "Driver"),
                "state": row.state,
                "joined_at": row.joined_at,
                "offer_expires_at": row.offer_expires_at,
                "is_demonstration": row.is_demonstration,
            }
            for row in queue_rows
        ],
    }


@router.patch("/manager/chargers/{charger_id}")
def patch_charger(charger_id: UUID, body: ChargerUpdateIn, manager: User = Depends(require_manager), db: Session = Depends(get_db)) -> dict:
    charger = update_charger(
        db,
        manager,
        charger_id,
        display_name=body.display_name,
        app_status=body.app_status,
        service_capacity=body.service_capacity,
        capacity_supplied="service_capacity" in body.model_fields_set,
        port_types_to_add=body.port_types_to_add,
        timezone_name=body.timezone,
    )
    return {"id": charger.id, "app_status": charger.app_status, "service_capacity": charger.service_capacity, "display_name": charger.display_name}


@router.post("/manager/chargers/{charger_id}/sessions/{session_id}/close")
def close_session(
    charger_id: UUID,
    session_id: UUID,
    body: CloseSessionIn,
    manager: User = Depends(require_manager),
    db: Session = Depends(get_db),
) -> dict:
    session = manager_close(db, manager, charger_id, session_id, body.reason, body.idempotency_key, utcnow())
    return {"id": session.id, "state": session.state}


@router.post("/manager/chargers/{charger_id}/remind", status_code=204)
def remind(charger_id: UUID, body: RemindIn, manager: User = Depends(require_manager), db: Session = Depends(get_db)) -> None:
    send_manager_reminder(db, manager, charger_id, body.user_id)
