"""First-in-first-out app waiting list.

An outstanding unexpired offer reserves one configured slot, just as an active
session does. Capacity is an application setting, not a count of physical
connectors. Paused or offline chargers keep existing waiting entries but do
not make new offers.

Expired offers are reconciled on the server. A browser timer is only a display.
"""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import fail
from app.db.models import ChargingSession, QueueEntry, User
from app.services.notifications import notify, short_label
from app.services.participation import (
    ensure_free_to_participate,
    lock_charger,
    lock_user,
    offers_allowed,
    slot_counts,
)
from app.services.sessions import create_charging_session


def reconcile_charger(db: Session, charger, now: datetime) -> None:
    """Expire offers, honour a paused/offline stop, then offer free slots.

    The charger row is locked. Callers that already hold that lock are safe.
    """
    charger = lock_charger(db, charger.id)
    settings = get_settings()
    active = list(
        db.scalars(
            select(QueueEntry)
            .where(QueueEntry.charger_id == charger.id, QueueEntry.state.in_(("waiting", "offered")))
            .order_by(QueueEntry.joined_at, QueueEntry.id)
            .with_for_update()
        )
    )
    label = short_label(charger.display_name)
    for entry in active:
        if entry.state == "offered" and entry.offer_expires_at is not None and entry.offer_expires_at <= now:
            entry.state = "expired"
            entry.updated_at = now
            notify(
                db,
                user_id=entry.user_id,
                event_key=f"offer-expired:{entry.id}:{entry.offer_round}",
                title="Coordination offer expired",
                body=(
                    f"The ten-minute offer at {label} ended before it was accepted. "
                    "You can join the waiting list again if you are not already participating."
                ),
                destination="/app/queue",
            )
    db.flush()

    if charger.app_status in ("paused", "offline"):
        for entry in active:
            if entry.state != "offered":
                continue
            entry.state = "waiting"
            entry.offer_expires_at = None
            entry.updated_at = now
            notify(
                db,
                user_id=entry.user_id,
                event_key=f"offer-withdrawn:{entry.id}:{charger.status_version}",
                title="Coordination offer withdrawn",
                body=(
                    f"{label} is {charger.app_status}. Your waiting-list place is unchanged, "
                    "and no new offer will be made until the charger is available again."
                ),
                destination=f"/app/chargers/{charger.id}",
            )
        for entry in active:
            if entry.state != "waiting":
                continue
            notify(
                db,
                user_id=entry.user_id,
                event_key=f"charger-status:{charger.id}:{entry.user_id}:{charger.status_version}",
                title="Charger status changed",
                body=(
                    f"{label} is now {charger.app_status}. Waiting places are kept, "
                    "but new coordination offers are paused."
                ),
                destination=f"/app/chargers/{charger.id}",
            )
        return

    if not offers_allowed(charger):
        return

    sessions, offers = slot_counts(db, charger.id, now)
    free = int(charger.service_capacity) - sessions - offers
    if free <= 0:
        return
    waiting = list(
        db.scalars(
            select(QueueEntry)
            .where(QueueEntry.charger_id == charger.id, QueueEntry.state == "waiting")
            .order_by(QueueEntry.joined_at, QueueEntry.id)
            .with_for_update()
        )
    )
    for entry in waiting:
        if free <= 0:
            break
        already_charging = db.scalar(
            select(ChargingSession.id).where(
                ChargingSession.user_id == entry.user_id,
                ChargingSession.unplugged_at.is_(None),
            )
        )
        if already_charging is not None:
            continue
        entry.offer_round += 1
        entry.state = "offered"
        entry.offer_expires_at = now + timedelta(seconds=settings.offer_ttl_seconds)
        entry.updated_at = now
        notify(
            db,
            user_id=entry.user_id,
            event_key=f"offer-made:{entry.id}:{entry.offer_round}",
            title="A coordination offer is ready",
            body=(
                f"A slot at {label} is offered to you for ten minutes. "
                "This coordinates participating users. It does not reserve a physical bay."
            ),
            destination="/app/queue",
        )
        free -= 1


def reconcile_expired_once() -> int:
    """Expire due offers for every charger. Each charger is its own transaction."""
    from app.core.clock import utcnow
    from app.db.session import SessionLocal

    now = utcnow()
    with SessionLocal() as db:
        charger_ids = list(
            db.scalars(
                select(QueueEntry.charger_id)
                .where(QueueEntry.state == "offered", QueueEntry.offer_expires_at <= now)
                .distinct()
            )
        )
    processed = 0
    for charger_id in charger_ids:
        with SessionLocal() as db:
            from app.db.models import Charger

            charger = db.get(Charger, charger_id)
            if charger is None:
                continue
            reconcile_charger(db, charger, now)
            db.commit()
            processed += 1
    return processed


def join_queue(db: Session, user: User, charger_id: UUID, idempotency_key: str, now: datetime, port_type: str | None = None) -> QueueEntry:
    lock_user(db, user.id)
    existing = db.scalar(
        select(QueueEntry).where(QueueEntry.user_id == user.id, QueueEntry.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing
    ensure_free_to_participate(db, user.id)
    charger = lock_charger(db, charger_id)
    from app.services.ports import selected_port
    port_type = selected_port(db, charger_id, port_type)
    if not charger.coordination_enabled or not charger.service_capacity:
        fail(
            409,
            "coordination_disabled",
            "App coordination is not configured for this charger yet. A manager can set a service capacity.",
        )
    entry = QueueEntry(
        user_id=user.id,
        charger_id=charger.id,
        state="waiting",
        port_type=port_type,
        joined_at=now,
        offer_round=0,
        idempotency_key=idempotency_key,
        is_demonstration=user.is_demonstration,
        created_at=now,
        updated_at=now,
    )
    db.add(entry)
    db.flush()
    reconcile_charger(db, charger, now)
    return entry


def leave_queue(db: Session, user: User, now: datetime) -> QueueEntry:
    lock_user(db, user.id)
    preview = db.scalar(select(QueueEntry).where(QueueEntry.user_id == user.id, QueueEntry.state.in_(("waiting", "offered"))))
    if preview is None:
        fail(409, "not_waiting", "You do not have a waiting-list place or an open offer.")
    charger = lock_charger(db, preview.charger_id)
    entry = db.scalar(
        select(QueueEntry)
        .where(QueueEntry.user_id == user.id, QueueEntry.state.in_(("waiting", "offered")))
        .with_for_update().execution_options(populate_existing=True)
    )
    if entry is None:
        fail(409, "not_waiting", "You do not have a waiting-list place or an open offer.")
    entry.state = "left"
    entry.offer_expires_at = None
    entry.updated_at = now
    db.flush()
    reconcile_charger(db, charger, now)
    return entry


def accept_offer(db: Session, user: User, idempotency_key: str, now: datetime) -> ChargingSession:
    lock_user(db, user.id)
    replay = db.scalar(select(QueueEntry).where(QueueEntry.user_id == user.id, QueueEntry.accept_idempotency_key == idempotency_key))
    if replay is not None and replay.session_id is not None:
        session = db.get(ChargingSession, replay.session_id)
        if session is not None:
            return session
    preview = db.scalar(select(QueueEntry).where(QueueEntry.user_id == user.id, QueueEntry.state.in_(("waiting", "offered"))))
    if preview is None:
        fail(409, "no_offer", "You do not have a coordination offer to accept.")
    charger = lock_charger(db, preview.charger_id)
    entry = db.scalar(
        select(QueueEntry)
        .where(QueueEntry.user_id == user.id, QueueEntry.state.in_(("waiting", "offered")))
        .with_for_update().execution_options(populate_existing=True)
    )
    if entry is None:
        fail(409, "no_offer", "You do not have a coordination offer to accept.")
    if entry.state != "offered" or entry.offer_expires_at is None:
        fail(409, "no_offer", "Wait for an offer before starting. Joining the list does not skip earlier drivers.")
    # Reject without mutating. A failed request rolls back, so expiry and the
    # next offer are applied by reconcile_charger, which commits on its own.
    if entry.offer_expires_at <= now or not offers_allowed(charger):
        fail(409, "offer_expired", "This coordination offer has expired or the charger is not offering slots.")
    entry.state = "accepted"
    entry.offer_expires_at = None
    entry.accept_idempotency_key = idempotency_key
    entry.updated_at = now
    db.flush()
    session = create_charging_session(
        db,
        user=user,
        charger=charger,
        idempotency_key=idempotency_key,
        now=now,
        actor_id=user.id,
        source_label="Driver session report",
        port_type=entry.port_type,
    )
    entry.session_id = session.id
    db.flush()
    reconcile_charger(db, charger, now)
    return session


def queue_position(db: Session, entry: QueueEntry) -> int | None:
    if entry.state != "waiting":
        return None
    ahead = db.scalar(
        select(func.count())
        .select_from(QueueEntry)
        .where(
            QueueEntry.charger_id == entry.charger_id,
            QueueEntry.state == "waiting",
            or_(
                QueueEntry.joined_at < entry.joined_at,
                (QueueEntry.joined_at == entry.joined_at) & (QueueEntry.id < entry.id),
            ),
        )
    )
    return int(ahead or 0) + 1


def waiting_count(db: Session, charger_id: UUID) -> int:
    value = db.scalar(
        select(func.count()).select_from(QueueEntry).where(QueueEntry.charger_id == charger_id, QueueEntry.state == "waiting")
    )
    return int(value or 0)
