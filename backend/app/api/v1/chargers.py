"""Charger search and details.

Straight-line distance is calculated only when the browser sends a location the
user chose to share. It is not a driving time, and port types are observed
labels rather than a compatibility check.
"""

from datetime import date, datetime
from math import asin, cos, radians, sin, sqrt
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, noload, selectinload

from app.api.deps import current_user, require_driver, require_researcher
from app.core.clock import utcnow
from app.db.models import ChargeEstimate, Charger, ChargerPortType, ChargingSession, Favourite, ManagerAssignment, QueueEntry, User
from app.db.session import get_db
from app.ml.outlook import score_outlook
from app.ml.guidance import driver_guidance
from app.ml.runtime import get_runtime
from app.schemas import AssistantOut, ChargerActionIn
from app.services.accounts import add_favourite, remove_favourite
from app.services.queues import queue_position

router = APIRouter()


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = radians(lat1), radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lon2 - lon1)
    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    return round(2 * radius * asin(sqrt(a)), 2)


def charger_cards(
    db: Session,
    user: User,
    *,
    charger_ids: list[UUID] | None = None,
    query: str | None = None,
    port_type: str | None = None,
    app_status: str | None = None,
    favourites_only: bool = False,
    historical_only: bool = False,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict], int]:
    statement = select(Charger).options(selectinload(Charger.port_types)).order_by(Charger.display_name, Charger.station_key)
    if charger_ids is not None:
        if not charger_ids:
            return [], 0
        statement = statement.where(Charger.id.in_(charger_ids))
    if query:
        pattern = _like(query.strip())
        statement = statement.where(
            or_(Charger.display_name.ilike(pattern, escape="\\"), Charger.station_key.ilike(pattern, escape="\\"))
        )
    if app_status:
        statement = statement.where(Charger.app_status == app_status)
    if historical_only:
        statement = statement.where(Charger.is_historical.is_(True))
    if port_type:
        statement = statement.where(
            Charger.id.in_(select(ChargerPortType.charger_id).where(ChargerPortType.name == port_type))
        )
    favourite_ids = set(db.scalars(select(Favourite.charger_id).where(Favourite.user_id == user.id)))
    if favourites_only:
        if not favourite_ids:
            return [], 0
        statement = statement.where(Charger.id.in_(favourite_ids))
    # Distance sorting happens after the rows are loaded, because straight-line
    # kilometres are not a database column. The cap keeps that path bounded.
    safety_cap = 2000
    # Count without the relationship loader. A loader option cannot be turned into a subquery.
    count_statement = statement.order_by(None).options(noload(Charger.port_types))
    total = int(db.scalar(select(func.count()).select_from(count_statement.subquery())) or 0)
    locating = origin_lat is not None and origin_lon is not None
    if locating:
        chargers = list(db.scalars(statement.limit(safety_cap)))
    elif limit is None:
        chargers = list(db.scalars(statement.limit(safety_cap)))
    else:
        chargers = list(db.scalars(statement.offset(offset).limit(limit)))
    waiting = dict(
        db.execute(
            select(QueueEntry.charger_id, func.count()).where(QueueEntry.state == "waiting").group_by(QueueEntry.charger_id)
        ).all()
    )
    active = dict(
        db.execute(
            select(ChargingSession.charger_id, func.count())
            .where(ChargingSession.unplugged_at.is_(None))
            .group_by(ChargingSession.charger_id)
        ).all()
    )
    cards = []
    next_targets = dict(db.execute(select(ChargingSession.charger_id, func.min(ChargeEstimate.estimated_target_at))
        .join(ChargeEstimate, ChargeEstimate.session_id == ChargingSession.id)
        .where(ChargingSession.unplugged_at.is_(None), ChargingSession.state == "charging", ChargeEstimate.is_active.is_(True), ChargeEstimate.estimated_target_at > utcnow())
        .group_by(ChargingSession.charger_id)).all())
    for charger in chargers:
        distance = None
        if origin_lat is not None and origin_lon is not None and charger.coordinates_on_map and charger.latitude is not None and charger.longitude is not None:
            distance = _distance_km(origin_lat, origin_lon, charger.latitude, charger.longitude)
        cards.append(
            {
                "id": charger.id,
                "station_key": charger.station_key,
                "display_name": charger.display_name,
                "is_historical": charger.is_historical,
                "latitude": charger.latitude if charger.coordinates_on_map else None,
                "longitude": charger.longitude if charger.coordinates_on_map else None,
                "coordinates_on_map": charger.coordinates_on_map,
                "coordinate_flag": charger.coordinate_flag,
                "app_status": charger.app_status,
                "status_updated_at": charger.status_updated_at,
                "status_source": "Driver session report" if (charger.status_source or "").startswith("Session report:") else charger.status_source,
                "timezone": charger.timezone_name,
                "coordination_enabled": charger.coordination_enabled,
                "service_capacity": charger.service_capacity,
                "port_types": [{"name": item.name, "origin": item.origin, "power_kw": item.power_kw, "charging_kind": item.charging_kind, "power_updated_at": item.power_updated_at} for item in charger.port_types],
                "is_favourite": charger.id in favourite_ids,
                "straight_line_km": distance,
                "waiting_count": int(waiting.get(charger.id, 0)),
                "active_session_count": int(active.get(charger.id, 0)),
                "next_estimated_target_at": next_targets.get(charger.id),
            }
        )
    if locating:
        cards.sort(key=lambda item: (item["straight_line_km"] is None, item["straight_line_km"] or 0, item["display_name"]))
        total = min(total, safety_cap)
        if limit is not None:
            cards = cards[offset : offset + limit]
    return cards, total


@router.get("/port-types")
def port_types(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    del user
    names = db.scalars(select(ChargerPortType.name).distinct().order_by(ChargerPortType.name)).all()
    return {"items": list(names)}


@router.get("/chargers")
def list_chargers(
    q: str | None = None,
    port_type: str | None = None,
    app_status: str | None = None,
    favourites_only: bool = False,
    historical_only: bool = False,
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    items, total = charger_cards(
        db,
        user,
        query=q,
        port_type=port_type,
        app_status=app_status,
        favourites_only=favourites_only,
        historical_only=historical_only,
        origin_lat=latitude,
        origin_lon=longitude,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "truncated": offset + len(items) < total,
        "distance_label": "straight-line distance" if latitude is not None and longitude is not None else None,
    }


@router.get("/chargers/{charger_id}")
def charger_detail(charger_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    cards, _total = charger_cards(db, user, charger_ids=[charger_id])
    if not cards:
        from app.core.errors import fail

        fail(404, "not_found", "Charger not found.")
    card = cards[0]
    managers = db.execute(
        select(User.display_name)
        .join(ManagerAssignment, ManagerAssignment.manager_id == User.id)
        .where(ManagerAssignment.charger_id == charger_id)
        .order_by(User.display_name)
    ).all()
    entry = db.scalar(
        select(QueueEntry).where(
            QueueEntry.user_id == user.id,
            QueueEntry.charger_id == charger_id,
            QueueEntry.state.in_(("waiting", "offered")),
        )
    )
    session = db.scalar(
        select(ChargingSession).where(
            ChargingSession.user_id == user.id,
            ChargingSession.charger_id == charger_id,
            ChargingSession.unplugged_at.is_(None),
        )
    )
    from app.services.coordination import public_departures
    card.update(
        {
            "manager_names": [row[0] for row in managers],
            "your_queue_state": entry.state if entry else None,
            "your_queue_position": queue_position(db, entry) if entry else None,
            "your_offer_expires_at": entry.offer_expires_at if entry else None,
            "your_session_id": session.id if session else None,
            "departure_reports": public_departures(db, charger_id, utcnow()),
            "server_time": utcnow(),
        }
    )
    return card


@router.get("/chargers/{charger_id}/outlook")
def charger_outlook(
    charger_id: UUID,
    arrival_date: date = date(2020, 6, 15),
    port_type: str | None = None,
    arrival_hour: int = Query(8, ge=0, le=23),
    user: User = Depends(require_researcher),
    db: Session = Depends(get_db),
) -> dict:
    del user
    charger = db.scalar(select(Charger).where(Charger.id == charger_id).options(selectinload(Charger.port_types)))
    if charger is None:
        from app.core.errors import fail

        fail(404, "not_found", "Charger not found.")
    ports = [item.name for item in sorted(charger.port_types, key=lambda item: (item.origin != "historical", item.name))]
    return score_outlook(
        charger.station_key, ports, arrival_date=arrival_date, port_type=port_type, arrival_hour=arrival_hour
    )


@router.get("/chargers/{charger_id}/guidance", response_model=AssistantOut, response_model_exclude_none=True)
def charger_guidance(
    charger_id: UUID,
    port_type: str | None = Query(default=None, max_length=120),
    planned_arrival: datetime | None = Query(default=None, description="Future local date/time in the station's time zone, without an offset; up to 7 days ahead. Read-only preview."),
    user: User = Depends(require_driver),
    db: Session = Depends(get_db),
) -> dict:
    charger = db.scalar(select(Charger).where(Charger.id == charger_id).options(selectinload(Charger.port_types)))
    if charger is None:
        from app.core.errors import fail

        fail(404, "not_found", "Charger not found.")
    return driver_guidance(db, user, charger, port_type=port_type, planned_arrival=planned_arrival, now=utcnow())


@router.post("/favourites", status_code=201)
def create_favourite(body: ChargerActionIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    # The idempotency key is accepted so the client can retry safely. The unique
    # favourite pair is what actually prevents duplicates.
    del body.idempotency_key
    add_favourite(db, user, body.charger_id)
    return {"saved": True}


@router.delete("/favourites/{charger_id}", status_code=204)
def delete_favourite(charger_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    remove_favourite(db, user, charger_id)
