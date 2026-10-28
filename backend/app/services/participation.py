"""Shared locks and the one-active-participation rule.

Driver actions lock the acting user row first and the charger row second.
Background expiry locks only the charger row. Do not lock a user after locking
a charger; that order can deadlock with a driver action.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import fail
from app.db.models import Charger, ChargingSession, QueueEntry, User

ACTIVE_QUEUE_STATES = ("waiting", "offered")


def lock_user(db: Session, user_id: UUID) -> User:
    user = db.scalar(select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True))
    if user is None:
        fail(404, "not_found", "Account not found.")
    return user


def lock_charger(db: Session, charger_id: UUID) -> Charger:
    charger = db.scalar(select(Charger).where(Charger.id == charger_id).with_for_update().execution_options(populate_existing=True))
    if charger is None:
        fail(404, "not_found", "Charger not found.")
    return charger


def slot_counts(db: Session, charger_id: UUID, now: datetime) -> tuple[int, int]:
    """Return active sessions and unexpired offers. Each reserves one app slot."""
    sessions = db.scalar(
        select(func.count())
        .select_from(ChargingSession)
        .where(ChargingSession.charger_id == charger_id, ChargingSession.unplugged_at.is_(None))
    )
    offers = db.scalar(
        select(func.count())
        .select_from(QueueEntry)
        .where(
            QueueEntry.charger_id == charger_id,
            QueueEntry.state == "offered",
            QueueEntry.offer_expires_at > now,
        )
    )
    return int(sessions or 0), int(offers or 0)


def offers_allowed(charger: Charger) -> bool:
    return bool(
        charger.coordination_enabled
        and charger.service_capacity
        and charger.service_capacity >= 1
        and charger.app_status not in ("paused", "offline")
    )


def find_participation(db: Session, user_id: UUID) -> tuple[str, UUID] | None:
    session = db.scalar(
        select(ChargingSession).where(
            ChargingSession.user_id == user_id,
            ChargingSession.unplugged_at.is_(None),
        )
    )
    if session is not None:
        return "session", session.charger_id
    entry = db.scalar(
        select(QueueEntry).where(
            QueueEntry.user_id == user_id,
            QueueEntry.state.in_(ACTIVE_QUEUE_STATES),
        )
    )
    if entry is not None:
        return "queue", entry.charger_id
    return None


def ensure_free_to_participate(db: Session, user_id: UUID) -> None:
    found = find_participation(db, user_id)
    if found is None:
        return
    kind, charger_id = found
    charger = db.get(Charger, charger_id)
    name = charger.display_name if charger is not None else "another charger"
    if kind == "session":
        message = (
            f"You already have an open charging session at {name}. "
            "Report that you have unplugged before joining a waiting list or starting elsewhere."
        )
    else:
        message = (
            f"You are already waiting, or holding an offer, at {name}. "
            "Leave that waiting list before joining a different charger."
        )
    fail(409, "active_participation", message, charger_id=str(charger_id), kind=kind)
