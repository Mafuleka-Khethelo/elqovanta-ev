"""Read-only operational oversight. Never returns passwords, tokens or ML data."""
from datetime import timedelta
from uuid import UUID

from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.clock import utcnow
from app.core.errors import fail
from app.db.models import (
    AssistantReminder, ChargeEstimate, Charger, ChargerReport, ChargingInterval,
    ChargingSession, Conversation, Favourite, ManagerAssignment, Message,
    QueueEntry, ReadMarker, User, Vehicle,
)
from app.services.sessions import session_seconds


def _count(db, statement):
    return int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)


def _directory(db, admin, *, q="", status="all", charger_id=None, days=0, needs_attention=False):
    now = utcnow()
    # Session-period filters apply to reported session totals, not current state.
    sessions = select(ChargingSession).where(ChargingSession.user_id == User.id)
    queues = select(QueueEntry).where(QueueEntry.user_id == User.id)
    reports = select(ChargerReport).where(ChargerReport.reporter_id == User.id)
    conversations = select(Conversation).where(Conversation.driver_id == User.id)
    if charger_id:
        if db.get(Charger, charger_id) is None:
            fail(404, "not_found", "Charger not found.")
        sessions = sessions.where(ChargingSession.charger_id == charger_id)
        queues = queues.where(QueueEntry.charger_id == charger_id)
        reports = reports.where(ChargerReport.charger_id == charger_id)
        conversations = conversations.where(Conversation.charger_id == charger_id)

    active = sessions.where(ChargingSession.unplugged_at.is_(None))
    waiting = queues.where(QueueEntry.state == "waiting")
    offered = queues.where(QueueEntry.state == "offered", QueueEntry.offer_expires_at > now)
    expired = queues.where(QueueEntry.state == "offered", QueueEntry.offer_expires_at <= now)
    current_state = case(
        (exists(active.where(ChargingSession.state == "charging")), "charging"),
        (exists(active.where(ChargingSession.state == "finished_plugged")), "finished_plugged"),
        (exists(active), "connected"),
        (exists(offered), "offered"), (exists(expired), "offer_expired"),
        (exists(waiting), "waiting"), else_="idle",
    ).label("activity_state")
    # Only messages this manager is assigned to read contribute to their unread
    # count. Administrator oversight does not alter conversation permissions.
    unread_messages = (
        select(func.count()).select_from(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .join(ManagerAssignment, (ManagerAssignment.charger_id == Conversation.charger_id) & (ManagerAssignment.manager_id == admin.id))
        .outerjoin(ReadMarker, (ReadMarker.conversation_id == Conversation.id) & (ReadMarker.user_id == admin.id))
        .where(Conversation.driver_id == User.id, Message.sender_id != admin.id,
               or_(ReadMarker.last_read_at.is_(None), Message.created_at > ReadMarker.last_read_at))
    )
    if charger_id:
        unread_messages = unread_messages.where(Conversation.charger_id == charger_id)
    open_reports = reports.where(ChargerReport.state != "resolved")
    vehicle_count = select(func.count()).select_from(Vehicle).where(Vehicle.user_id == User.id).scalar_subquery()
    favourites = select(func.count()).select_from(Favourite).where(Favourite.user_id == User.id)
    if charger_id:
        favourites = favourites.where(Favourite.charger_id == charger_id)

    # Correlated count queries keep filters and pagination in PostgreSQL.
    base = select(User.id, User.email, User.display_name, User.created_at, User.is_demonstration,
        current_state, vehicle_count.label("vehicle_count"), favourites.scalar_subquery().label("favourite_count"),
        open_reports.with_only_columns(func.count()).scalar_subquery().label("open_reports"),
        unread_messages.scalar_subquery().label("unread_messages"),
    ).where(User.role == "driver")
    if q.strip():
        base = base.where(or_(User.display_name.icontains(q.strip(), autoescape=True), User.email.icontains(q.strip(), autoescape=True)))
    if charger_id:
        base = base.where(or_(exists(sessions), exists(queues), exists(reports), exists(conversations),
            exists(select(Favourite.user_id).where(Favourite.user_id == User.id, Favourite.charger_id == charger_id))))
    if status == "no_vehicle":
        base = base.where(vehicle_count == 0)
    elif status == "has_favourites":
        base = base.where(favourites.scalar_subquery() > 0)
    elif status != "all":
        base = base.where(current_state == status)
    if needs_attention:
        base = base.where(or_(current_state.in_(("finished_plugged", "offer_expired")), exists(open_reports), unread_messages.scalar_subquery() > 0))
    return base, now


def _session_totals(db, user_ids, days, now, charger_id=None):
    # Aggregate intervals first to avoid multiplying session counts by intervals.
    interval_seconds = select(ChargingInterval.session_id,
        func.sum(func.extract("epoch", func.coalesce(ChargingInterval.ended_at, now) - ChargingInterval.started_at)).label("charging")
    ).group_by(ChargingInterval.session_id).subquery()
    connected = func.extract("epoch", func.coalesce(ChargingSession.unplugged_at, now) - ChargingSession.plugged_in_at)
    charging = func.coalesce(interval_seconds.c.charging, 0)
    statement = select(ChargingSession.user_id,
        func.count().label("sessions"),
        func.count(ChargingSession.unplugged_at).label("completed"),
        func.sum(func.greatest(connected, 0)).label("connected_seconds"),
        func.sum(func.greatest(charging, 0)).label("charging_seconds"),
        func.sum(func.greatest(connected - charging, 0)).label("noncharging_seconds"),
        func.max(ChargingSession.plugged_in_at).label("last_session_at"),
    ).outerjoin(interval_seconds, interval_seconds.c.session_id == ChargingSession.id).where(ChargingSession.user_id.in_(user_ids))
    if days:
        statement = statement.where(ChargingSession.plugged_in_at >= now - timedelta(days=days))
    if charger_id:
        statement = statement.where(ChargingSession.charger_id == charger_id)
    rows = db.execute(statement.group_by(ChargingSession.user_id)).mappings()
    return {row["user_id"]: {key: (int(value or 0) if key.endswith("seconds") or key in ("sessions", "completed") else value)
        for key, value in row.items() if key != "user_id"} for row in rows}


def directory(db: Session, admin: User, *, limit=20, offset=0, **filters):
    base, now = _directory(db, admin, **filters)
    matched = base.subquery()
    summary = dict(db.execute(select(func.count().label("drivers"),
        *[func.count().filter(matched.c.activity_state == state).label(state) for state in
          ("charging", "finished_plugged", "waiting", "offered", "offer_expired", "idle", "connected")],
        func.coalesce(func.sum(matched.c.open_reports), 0).label("open_reports"),
        func.coalesce(func.sum(matched.c.unread_messages), 0).label("unread_messages"),
    )).mappings().one())
    summary = {key: int(value) for key, value in summary.items()}
    rows = [dict(row) for row in db.execute(base.order_by(User.display_name, User.id).offset(offset).limit(limit)).mappings()]
    totals = _session_totals(db, select(matched.c.id), filters.get("days", 0), now, filters.get("charger_id"))
    summary["completed_sessions"] = sum(row["completed"] for row in totals.values())
    summary["noncharging_seconds"] = sum(row["noncharging_seconds"] for row in totals.values())
    for row in rows:
        row["session_summary"] = totals.get(row["id"], {"sessions": 0, "completed": 0, "connected_seconds": 0,
            "charging_seconds": 0, "noncharging_seconds": 0, "last_session_at": None})
    return {"items": rows, "total": summary["drivers"], "limit": limit, "offset": offset,
        "summary": summary, "server_time": now, "session_period_days": filters.get("days", 0),
        "chargers": [{"id": row.id, "display_name": row.display_name} for row in db.scalars(select(Charger).order_by(Charger.display_name))]}


def driver_detail(db: Session, admin: User, driver_id: UUID, *, limit=10, offset=0, days=0, charger_id=None):
    driver = db.get(User, driver_id)
    if driver is None or driver.role != "driver":
        fail(404, "not_found", "Driver not found.")
    now = utcnow()
    base = select(ChargingSession).where(ChargingSession.user_id == driver.id)
    if days:
        base = base.where(ChargingSession.plugged_in_at >= now - timedelta(days=days))
    if charger_id:
        if db.get(Charger, charger_id) is None:
            fail(404, "not_found", "Charger not found.")
        base = base.where(ChargingSession.charger_id == charger_id)
    total = _count(db, base)
    sessions = list(db.scalars(base.options(selectinload(ChargingSession.intervals)).order_by(ChargingSession.plugged_in_at.desc(), ChargingSession.id).offset(offset).limit(limit)))
    session_ids = [row.id for row in sessions]
    estimates = {}
    for estimate in db.scalars(select(ChargeEstimate).where(ChargeEstimate.session_id.in_(session_ids)).order_by(ChargeEstimate.version)):
        estimates[estimate.session_id] = estimate
    reminders = {row.session_id: row for row in db.scalars(select(AssistantReminder).where(AssistantReminder.session_id.in_(session_ids)))}
    assigned = set(db.scalars(select(ManagerAssignment.charger_id).where(ManagerAssignment.manager_id == admin.id)))
    chargers = {row.id: row for row in db.scalars(select(Charger))}
    def station(key):
        charger = chargers.get(key)
        return {"charger_id": key, "charger_name": charger.display_name if charger else "Charger", "can_manage": key in assigned}
    session_rows = []
    for row in sessions:
        estimate, reminder = estimates.get(row.id), reminders.get(row.id)
        session_rows.append({"id": row.id, **station(row.charger_id), "state": row.state, "port_type": row.port_type,
            "plugged_in_at": row.plugged_in_at, "unplugged_at": row.unplugged_at, "is_demonstration": row.is_demonstration,
            **session_seconds(row, list(row.intervals), now),
            "estimate": None if estimate is None else {"vehicle_label": estimate.vehicle_label,
                "current_percent": estimate.current_percent, "target_percent": estimate.target_percent,
                "estimated_target_at": estimate.estimated_target_at, "is_estimate": True},
            "reminder": None if reminder is None else {"enabled": reminder.enabled, "due_at": reminder.due_at, "delivered_at": reminder.delivered_at}})
    report_query = select(ChargerReport).where(ChargerReport.reporter_id == driver.id)
    threads_query = select(Conversation).where(Conversation.driver_id == driver.id)
    favourites_query = select(Favourite).where(Favourite.user_id == driver.id)
    queue_query = select(QueueEntry).where(QueueEntry.user_id == driver.id, QueueEntry.state.in_(("waiting", "offered")))
    if charger_id:
        report_query = report_query.where(ChargerReport.charger_id == charger_id)
        threads_query = threads_query.where(Conversation.charger_id == charger_id)
        favourites_query = favourites_query.where(Favourite.charger_id == charger_id)
        queue_query = queue_query.where(QueueEntry.charger_id == charger_id)
    queue = db.scalar(queue_query)
    return {"driver": {"id": driver.id, "display_name": driver.display_name, "email": driver.email,
            "created_at": driver.created_at, "is_demonstration": driver.is_demonstration},
        "server_time": now, "session_period_days": days,
        "sessions": {"items": session_rows, "total": total, "limit": limit, "offset": offset},
        "session_summary": _session_totals(db, [driver.id], days, now, charger_id).get(driver.id),
        "vehicles": [{"id": row.id, "nickname": row.nickname, "model_name": row.model_name,
            "battery_capacity_kwh": row.battery_capacity_kwh, "max_ac_kw": row.max_ac_kw, "max_dc_kw": row.max_dc_kw}
            for row in db.scalars(select(Vehicle).where(Vehicle.user_id == driver.id).order_by(Vehicle.created_at))],
        "queue": None if queue is None else {**station(queue.charger_id), "state": queue.state,
            "joined_at": queue.joined_at, "offer_expires_at": queue.offer_expires_at},
        "favourites": {"total": _count(db, favourites_query), "items": [station(row.charger_id)
            for row in db.scalars(favourites_query.order_by(Favourite.created_at.desc()).limit(20))]},
        "reports": {"total": _count(db, report_query), "items": [{"id": row.id, **station(row.charger_id),
            "category": row.category, "state": row.state, "details": row.details, "manager_response": row.manager_response,
            "created_at": row.created_at} for row in db.scalars(report_query.order_by(ChargerReport.created_at.desc()).limit(20))]},
        "conversations": {"total": _count(db, threads_query), "items": [{"id": row.id, **station(row.charger_id),
            "created_at": row.created_at} for row in db.scalars(threads_query.order_by(Conversation.created_at.desc()).limit(20))]}}
