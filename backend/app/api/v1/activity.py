"""Sessions, waiting list, notifications and messages."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_driver
from app.core.clock import utcnow
from app.core.errors import fail
from app.db.models import AssistantReminder, ChargeEstimate, Charger, ChargingInterval, ChargingSession, Conversation, Message, Notification, QueueEntry, SessionEvent, User
from app.db.session import get_db
from app.schemas import ChargerActionIn, ConversationIn, IdKeyIn, MessageIn, SessionStartIn, OfferAcceptIn
from app.services.messages import list_conversations, list_messages, mark_read, open_conversation, require_conversation, send_message, unread_count
from app.services.queues import accept_offer, join_queue, leave_queue, queue_position, waiting_count
from app.services.sessions import driver_action, direct_start, report_still_charging, session_seconds
from app.services.manager import send_driver_reminder

router = APIRouter()


def _session_payload(db: Session, session: ChargingSession, now: datetime) -> dict:
    intervals = list(
        db.scalars(select(ChargingInterval).where(ChargingInterval.session_id == session.id).order_by(ChargingInterval.started_at))
    )
    events = list(db.scalars(select(SessionEvent).where(SessionEvent.session_id == session.id).order_by(SessionEvent.created_at)))
    charger = db.get(Charger, session.charger_id)
    actor_ids = {event.actor_user_id for event in events if event.actor_user_id}
    names = {}
    if actor_ids:
        names = {row.id: row.display_name for row in db.scalars(select(User).where(User.id.in_(actor_ids)))}
    estimate = db.scalar(select(ChargeEstimate).where(ChargeEstimate.session_id == session.id).order_by(ChargeEstimate.version.desc()).limit(1))
    reminder = db.get(AssistantReminder, session.id)
    return {
        "id": session.id,
        "charger_id": session.charger_id,
        "charger_name": charger.display_name if charger else "Charger",
        "station_key": charger.station_key if charger else "",
        "state": session.state,
        "port_type": session.port_type,
        "plugged_in_at": session.plugged_in_at,
        "unplugged_at": session.unplugged_at,
        "is_demonstration": session.is_demonstration,
        "charge_summary": None if estimate is None else {"vehicle_label": estimate.vehicle_label,
            "target_percent": estimate.target_percent, "last_entered_percent": estimate.current_percent,
            "estimated_target_at": estimate.estimated_target_at, "is_estimate": True},
        "return_reminder_sent_at": reminder.delivered_at if reminder else None,
        **session_seconds(session, intervals, now),
        "intervals": [{"started_at": item.started_at, "ended_at": item.ended_at} for item in intervals],
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "reason": event.reason,
                "created_at": event.created_at,
                "actor_name": names.get(event.actor_user_id),
            }
            for event in events
        ],
    }


@router.get("/sessions/current")
def current_session(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    session = db.scalar(
        select(ChargingSession).where(ChargingSession.user_id == user.id, ChargingSession.unplugged_at.is_(None))
    )
    if session is None:
        return {"session": None, "server_time": utcnow()}
    return {"session": _session_payload(db, session, utcnow()), "server_time": utcnow()}


@router.get("/sessions/history")
def session_history(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    base = select(ChargingSession).where(ChargingSession.user_id == user.id, ChargingSession.unplugged_at.is_not(None))
    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = list(
        db.scalars(base.order_by(ChargingSession.unplugged_at.desc()).offset(offset).limit(limit))
    )
    now = utcnow()
    return {"items": [_session_payload(db, row, now) for row in rows], "total": total, "limit": limit, "offset": offset}


@router.post("/sessions", status_code=201)
def start_session(body: SessionStartIn, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    session = direct_start(db, user, body.charger_id, body.idempotency_key, utcnow(), body.port_type)
    if body.charge_estimate is not None:
        # Save the session's reported-status change before the estimate service
        # locks/refreshes the same charger in this transaction.
        db.flush()
        from hashlib import sha256
        from app.services.charging_estimates import save
        save(db, user, session.id, body.charge_estimate, "start:"+sha256(body.idempotency_key.encode()).hexdigest(), 0, utcnow(), at_start=True)
    return {"session": _session_payload(db, session, utcnow())}


def _act(action: str):
    def endpoint(session_id: UUID, body: IdKeyIn, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
        session = driver_action(db, user, session_id, action, body.idempotency_key, utcnow())
        return {"session": _session_payload(db, session, utcnow())}

    endpoint.__name__ = f"{action}_session"
    return endpoint


# Compatibility for already-open old clients and historical interval tests.
# New driver pages expose finish and unplug only; these are not hardware controls.
router.post("/sessions/{session_id}/pause", deprecated=True)(_act("pause"))
router.post("/sessions/{session_id}/resume", deprecated=True)(_act("resume"))
router.post("/sessions/{session_id}/finish")(_act("finish"))
router.post("/sessions/{session_id}/unplug")(_act("unplug"))


@router.post("/sessions/{session_id}/still-charging", status_code=204)
def still_charging(session_id: UUID, body: IdKeyIn, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> None:
    report_still_charging(db, user, session_id, body.idempotency_key, utcnow())


@router.get("/queue")
def my_queue(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    now = utcnow()
    from app.services.queues import reconcile_charger

    entry = db.scalar(
        select(QueueEntry).where(QueueEntry.user_id == user.id, QueueEntry.state.in_(("waiting", "offered")))
    )
    session = db.scalar(
        select(ChargingSession).where(ChargingSession.user_id == user.id, ChargingSession.unplugged_at.is_(None))
    )
    if entry is not None and entry.state == "offered" and entry.offer_expires_at is not None and entry.offer_expires_at <= now:
        charger = db.get(Charger, entry.charger_id)
        if charger is not None:
            reconcile_charger(db, charger, now)
            db.flush()
            entry = db.scalar(
                select(QueueEntry).where(QueueEntry.user_id == user.id, QueueEntry.state.in_(("waiting", "offered")))
            )
    charger = db.get(Charger, entry.charger_id) if entry else (db.get(Charger, session.charger_id) if session else None)
    participation = "none"
    if session is not None:
        participation = "session"
    elif entry is not None:
        participation = entry.state
    return {
        "participation": participation,
        "port_type": entry.port_type if entry else (session.port_type if session else None),
        "server_time": now,
        "position": queue_position(db, entry) if entry is not None else None,
        "waiting_count": waiting_count(db, entry.charger_id) if entry is not None else None,
        "offer_expires_at": entry.offer_expires_at if entry is not None else None,
        "session_id": session.id if session is not None else (entry.session_id if entry else None),
        "charge_plan": entry.charge_plan if entry and entry.state in ("waiting", "offered") else None,
        "charger": None
        if charger is None
        else {"id": charger.id, "display_name": charger.display_name, "app_status": charger.app_status, "timezone": charger.timezone_name},
    }


@router.post("/queue/join")
def post_join(body: SessionStartIn, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    entry = join_queue(db, user, body.charger_id, body.idempotency_key, utcnow(), body.port_type)
    if body.charge_estimate is not None and entry.charge_plan is None:
        from app.services.charging_estimates import preview
        if body.charge_estimate.charger_id and body.charge_estimate.charger_id != body.charger_id:
            fail(422, "charger_mismatch", "The plan belongs to a different charger.")
        preview(db, user, body.charge_estimate, utcnow())
        entry.charge_plan = body.charge_estimate.model_dump(mode="json")
    return {"state": entry.state, "charger_id": entry.charger_id, "offer_expires_at": entry.offer_expires_at, "position": queue_position(db, entry)}


@router.post("/queue/leave")
def post_leave(user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    entry = leave_queue(db, user, utcnow())
    return {"state": entry.state}


@router.post("/queue/accept", status_code=201)
def post_accept(body: OfferAcceptIn, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    session = accept_offer(db, user, body.idempotency_key, utcnow())
    # Use the freshly confirmed reading, never a potentially old queue preview.
    # Old clients may omit it; their original coordination flow remains valid.
    if body.charge_estimate is not None:
        db.flush()
        from hashlib import sha256
        from app.services.charging_estimates import save
        save(db, user, session.id, body.charge_estimate, "accept:"+sha256(body.idempotency_key.encode()).hexdigest(), 0, utcnow(), at_start=True)
    return {"session": _session_payload(db, session, utcnow())}


@router.post("/queue/remind", status_code=204)
def post_remind(body: ChargerActionIn, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> None:
    del body.idempotency_key
    send_driver_reminder(db, user, body.charger_id)


@router.get("/notifications")
def notifications(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    base = select(Notification).where(Notification.user_id == user.id)
    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = list(db.scalars(base.order_by(Notification.created_at.desc()).offset(offset).limit(limit)))
    return {
        "items": [
            {
                "id": row.id,
                "title": row.title,
                "body": row.body,
                "destination": row.destination,
                "read_at": row.read_at,
                "created_at": row.created_at,
            }
            for row in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/notifications/unread-count")
def unread_notifications(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    count = db.scalar(
        select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return {"unread": int(count or 0)}


@router.post("/notifications/{notification_id}/read", status_code=204)
def read_notification(notification_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    note = db.get(Notification, notification_id)
    if note is None or note.user_id != user.id:
        fail(404, "not_found", "Notification not found.")
    if note.read_at is None:
        note.read_at = utcnow()


@router.post("/notifications/read-all", status_code=204)
def read_all(user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    now = utcnow()
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None)))
    for note in rows:
        note.read_at = now


@router.get("/conversations")
def conversations(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    items = []
    for conversation in list_conversations(db, user):
        charger = db.get(Charger, conversation.charger_id)
        last = db.scalar(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at.desc()).limit(1))
        other = _other_party(db, user, conversation)
        items.append(
            {
                "id": conversation.id,
                "charger_id": conversation.charger_id,
                "charger_name": charger.display_name if charger else "Charger",
                "other_name": other,
                "unread": unread_count(db, conversation.id, user.id),
                "last_body": last.body if last else None,
                "last_at": last.created_at if last else conversation.created_at,
            }
        )
    return {"items": items}


def _other_party(db: Session, user: User, conversation: Conversation) -> str:
    from app.db.models import ManagerAssignment

    if user.role == "manager":
        driver = db.get(User, conversation.driver_id)
        return driver.display_name if driver else "Driver"
    names = db.scalars(
        select(User.display_name)
        .join(ManagerAssignment, ManagerAssignment.manager_id == User.id)
        .where(ManagerAssignment.charger_id == conversation.charger_id)
        .order_by(User.display_name)
    ).all()
    return ", ".join(names) if names else "Station manager"


@router.post("/conversations", status_code=201)
def create_conversation(body: ConversationIn, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> dict:
    conversation = open_conversation(db, user, body.charger_id)
    return {"id": conversation.id}


@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: UUID,
    before: datetime | None = None,
    limit: int = Query(default=30, ge=1, le=50),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    conversation = require_conversation(db, user, conversation_id)
    rows, has_older = list_messages(db, conversation.id, before, limit)
    senders = {row.sender_id for row in rows}
    names = {person.id: person.display_name for person in db.scalars(select(User).where(User.id.in_(senders)))} if senders else {}
    return {
        "items": [
            {
                "id": row.id,
                "sender_id": row.sender_id,
                "sender_name": names.get(row.sender_id, "User"),
                "body": row.body,
                "created_at": row.created_at,
                "mine": row.sender_id == user.id,
            }
            for row in rows
        ],
        "has_older": has_older,
    }


@router.post("/conversations/{conversation_id}/messages", status_code=201)
def post_message(conversation_id: UUID, body: MessageIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    conversation = require_conversation(db, user, conversation_id)
    message = send_message(db, user, conversation, body.body, body.client_request_id)
    return {"id": message.id, "created_at": message.created_at, "body": message.body}


@router.post("/conversations/{conversation_id}/read", status_code=204)
def read_conversation(conversation_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    conversation = require_conversation(db, user, conversation_id)
    mark_read(db, conversation.id, user.id, utcnow())
