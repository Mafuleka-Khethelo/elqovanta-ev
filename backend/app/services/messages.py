"""Driver-to-assigned-manager conversations.

A driver sees only their own threads. A manager sees threads for chargers
assigned to them. There is no public group chat and no online indicator.
"""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import fail
from app.db.models import Charger, Conversation, ManagerAssignment, Message, ReadMarker, User
from app.services.notifications import notify, short_label


def open_conversation(db: Session, driver: User, charger_id: UUID) -> Conversation:
    if driver.role != "driver":
        fail(403, "drivers_only", "Only a driver can start a conversation with a station manager.")
    from app.services.participation import lock_user
    lock_user(db, driver.id)
    charger = db.get(Charger, charger_id)
    if charger is None:
        fail(404, "not_found", "Charger not found.")
    assigned = db.scalar(select(ManagerAssignment.id).where(ManagerAssignment.charger_id == charger_id))
    if assigned is None:
        fail(409, "no_manager", "No station manager is assigned to this charger yet, so there is nobody to message.")
    existing = db.scalar(
        select(Conversation).where(Conversation.charger_id == charger_id, Conversation.driver_id == driver.id)
    )
    if existing is not None:
        return existing
    conversation = Conversation(charger_id=charger_id, driver_id=driver.id, created_at=utcnow())
    db.add(conversation)
    db.flush()
    return conversation


def require_conversation(db: Session, user: User, conversation_id: UUID) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or not _can_view(db, user, conversation):
        fail(404, "not_found", "Conversation not found.")
    return conversation


def _can_view(db: Session, user: User, conversation: Conversation) -> bool:
    if user.role == "driver":
        return conversation.driver_id == user.id
    if user.role == "manager":
        assigned = db.scalar(
            select(ManagerAssignment.id).where(
                ManagerAssignment.manager_id == user.id,
                ManagerAssignment.charger_id == conversation.charger_id,
            )
        )
        return assigned is not None
    return False


def send_message(db: Session, user: User, conversation: Conversation, body: str, client_request_id: str) -> Message:
    from app.services.participation import lock_user
    lock_user(db, user.id)
    cleaned = body.strip()
    if not cleaned:
        fail(422, "empty_message", "Enter a message before sending.")
    if len(cleaned) > 2000:
        fail(422, "message_too_long", "Messages are limited to 2000 characters.")
    existing = db.scalar(select(Message).where(Message.client_request_id == client_request_id))
    if existing is not None:
        if existing.conversation_id != conversation.id or existing.sender_id != user.id or existing.body != cleaned:
            fail(409, "duplicate_request", "That message identifier was already used.")
        return existing
    now = utcnow()
    recent = db.scalar(
        select(func.count())
        .select_from(Message)
        .where(Message.sender_id == user.id, Message.created_at > now - timedelta(minutes=1))
    )
    if int(recent or 0) >= 20:
        fail(429, "too_many_messages", "Please wait a moment before sending more messages.")
    message = Message(
        conversation_id=conversation.id,
        sender_id=user.id,
        body=cleaned,
        client_request_id=client_request_id,
        created_at=now,
    )
    db.add(message)
    db.flush()
    mark_read(db, conversation.id, user.id, now)
    _notify_recipients(db, user, conversation, message)
    return message


def mark_read(db: Session, conversation_id: UUID, user_id: UUID, when: datetime) -> None:
    # Strict Mode, polling and multiple tabs may report the same read together.
    # The database arbitrates the first insert and never moves a marker back.
    statement = insert(ReadMarker).values(conversation_id=conversation_id, user_id=user_id, last_read_at=when)
    db.execute(statement.on_conflict_do_update(
        index_elements=[ReadMarker.conversation_id, ReadMarker.user_id],
        set_={"last_read_at": func.greatest(ReadMarker.last_read_at, statement.excluded.last_read_at)},
    ))


def unread_count(db: Session, conversation_id: UUID, user_id: UUID) -> int:
    marker = db.get(ReadMarker, (conversation_id, user_id))
    statement = select(func.count()).select_from(Message).where(
        Message.conversation_id == conversation_id,
        Message.sender_id != user_id,
    )
    if marker is not None:
        statement = statement.where(Message.created_at > marker.last_read_at)
    return int(db.scalar(statement) or 0)


def list_messages(db: Session, conversation_id: UUID, before: datetime | None, limit: int) -> tuple[list[Message], bool]:
    statement = select(Message).where(Message.conversation_id == conversation_id)
    if before is not None:
        statement = statement.where(Message.created_at < before)
    rows = list(db.scalars(statement.order_by(Message.created_at.desc()).limit(limit + 1)))
    has_older = len(rows) > limit
    page = list(reversed(rows[:limit]))
    return page, has_older


def list_conversations(db: Session, user: User) -> list[Conversation]:
    if user.role not in ("driver", "manager"):
        fail(403, "operations_only", "Private station conversations are for drivers and assigned managers.")
    if user.role == "driver":
        statement = select(Conversation).where(Conversation.driver_id == user.id)
    else:
        assigned_ids = select(ManagerAssignment.charger_id).where(ManagerAssignment.manager_id == user.id)
        statement = select(Conversation).where(Conversation.charger_id.in_(assigned_ids))
    conversations = list(db.scalars(statement))
    def latest(conversation: Conversation) -> datetime:
        value = db.scalar(select(func.max(Message.created_at)).where(Message.conversation_id == conversation.id))
        return value or conversation.created_at
    conversations.sort(key=latest, reverse=True)
    return conversations


def _notify_recipients(db: Session, sender: User, conversation: Conversation, message: Message) -> None:
    charger = db.get(Charger, conversation.charger_id)
    label = short_label(charger.display_name if charger else "a charger")
    preview = message.body if len(message.body) <= 140 else message.body[:137] + "..."
    if sender.role == "driver":
        recipients = list(
            db.scalars(select(ManagerAssignment.manager_id).where(ManagerAssignment.charger_id == conversation.charger_id))
        )
    else:
        recipients = [conversation.driver_id]
    for recipient_id in recipients:
        if recipient_id == sender.id:
            continue
        notify(
            db,
            user_id=recipient_id,
            event_key=f"message:{message.id}:{recipient_id}",
            title="New message",
            body=f"{sender.display_name} at {label}: {preview}",
            destination=f"/app/messages/{conversation.id}",
        )
