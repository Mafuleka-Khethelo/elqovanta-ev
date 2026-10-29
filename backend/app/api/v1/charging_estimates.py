from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_driver
from app.core.clock import utcnow
from app.core.errors import fail
from app.db.models import ChargeEstimate, Charger, ChargingSession, User
from app.db.session import get_db
from app.schemas import ChargeEstimateIn, EstimateUpdateIn
from app.services import charging_estimates as service
from app.services.coordination import own_session

router = APIRouter()


@router.post("/charging-estimates/preview")
def preview(body: ChargeEstimateIn, user: User = Depends(require_driver), db: Session = Depends(get_db)):
    return {"estimate": service.preview(db, user, body, utcnow()), "server_time": utcnow()}


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


@router.get("/chargers/{charger_id}/charging-estimates")
def station_estimates(charger_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if db.get(Charger, charger_id) is None:
        fail(404, "not_found", "Charger not found.")
    now = utcnow()
    return {**service.station_summary(db, charger_id, now), "timezone": db.get(Charger, charger_id).timezone_name}
