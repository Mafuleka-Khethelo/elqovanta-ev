"""Administrator-only read APIs, separate from station-manager assignments."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.errors import fail
from app.db.models import User
from app.db.session import get_db
from app.services import administration

router = APIRouter(prefix="/admin")
Status = Literal["all", "charging", "finished_plugged", "waiting", "offered", "offer_expired", "idle", "connected", "no_vehicle", "has_favourites"]


@router.get("/drivers")
def drivers(q: str = Query("", max_length=100), status: Status = "all", charger_id: UUID | None = None,
    days: int = Query(0, ge=0, le=90), needs_attention: bool = False, limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0), admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if days not in (0, 7, 30, 90):
        fail(422, "invalid_period", "Choose all time, 7, 30 or 90 days.")
    return administration.directory(db, admin, q=q, status=status, charger_id=charger_id, days=days,
        needs_attention=needs_attention, limit=limit, offset=offset)


@router.get("/drivers/{driver_id}")
def driver(driver_id: UUID, days: int = Query(0, ge=0, le=90), charger_id: UUID | None = None,
    limit: int = Query(10, ge=1, le=50), offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if days not in (0, 7, 30, 90):
        fail(422, "invalid_period", "Choose all time, 7, 30 or 90 days.")
    return administration.driver_detail(db, admin, driver_id, limit=limit, offset=offset, days=days, charger_id=charger_id)
