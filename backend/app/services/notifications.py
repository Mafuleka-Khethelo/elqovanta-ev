"""In-app notifications.

event_key makes repeated deliveries of the same fact harmless. Nothing in this
module sends email or SMS.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.db.models import Notification


def notify(
    db: Session,
    *,
    user_id: UUID,
    event_key: str,
    title: str,
    body: str,
    destination: str,
) -> Notification:
    existing = db.scalar(select(Notification).where(Notification.event_key == event_key))
    if existing is not None:
        return existing
    note = Notification(
        user_id=user_id,
        event_key=event_key[:200],
        title=title[:140],
        body=body[:500],
        destination=destination[:200],
        created_at=utcnow(),
    )
    try:
        with db.begin_nested():
            db.add(note)
            db.flush()
    except IntegrityError:
        return db.scalar(select(Notification).where(Notification.event_key == event_key))
    return note


def short_label(value: str, limit: int = 80) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
