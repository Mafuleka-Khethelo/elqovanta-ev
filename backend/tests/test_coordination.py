"""Queue capacity, offer expiry and reported session durations."""

import threading
import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.clock import utcnow
from app.core.security import hash_password
from app.db.models import Charger, ChargingSession, Notification, QueueEntry, User
from app.db.session import SessionLocal
from app.services.queues import accept_offer, join_queue, reconcile_charger
from app.services.sessions import direct_start, driver_action, session_seconds


def make_user(db, email: str) -> User:
    user = User(email=email, display_name=email.split("@")[0], password_hash=hash_password("correct-horse-battery"), role="driver")
    db.add(user)
    db.flush()
    return user


def make_charger(db, capacity: int = 1) -> Charger:
    charger = Charger(
        station_key=f"TEST / {uuid.uuid4()}",
        display_name="Test charger",
        app_status="available",
        status_source="Test",
        service_capacity=capacity,
        coordination_enabled=True,
        coordinate_flag="missing",
    )
    db.add(charger)
    db.flush()
    return charger


def test_repeated_join_does_not_duplicate(db):
    user = make_user(db, "join@example.com")
    charger = make_charger(db)
    db.commit()
    key = "join-key-001"
    now = utcnow()
    first = join_queue(db, user, charger.id, key, now)
    db.commit()
    second = join_queue(db, user, charger.id, key, now + timedelta(seconds=1))
    db.commit()
    assert first.id == second.id
    count = db.scalar(select(func.count()).select_from(QueueEntry).where(QueueEntry.user_id == user.id))
    assert count == 1


def test_two_drivers_cannot_take_the_last_slot(db):
    first = make_user(db, "first@example.com")
    second = make_user(db, "second@example.com")
    charger = make_charger(db, capacity=1)
    db.commit()
    barrier = threading.Barrier(2)
    results: list[int] = []

    def attempt(user_id):
        session = SessionLocal()
        try:
            user = session.get(User, user_id)
            barrier.wait(timeout=10)
            try:
                direct_start(session, user, charger.id, str(uuid.uuid4()), utcnow())
                session.commit()
                results.append(201)
            except HTTPException as exc:
                session.rollback()
                results.append(exc.status_code)
        finally:
            session.close()

    threads = [threading.Thread(target=attempt, args=(user.id,)) for user in (first, second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == [201, 409]
    with SessionLocal() as check:
        open_sessions = check.scalar(
            select(func.count()).select_from(ChargingSession).where(ChargingSession.unplugged_at.is_(None))
        )
        assert open_sessions == 1


def test_two_joins_produce_one_offer(db):
    first = make_user(db, "queue-a@example.com")
    second = make_user(db, "queue-b@example.com")
    charger = make_charger(db, capacity=1)
    db.commit()
    barrier = threading.Barrier(2)

    def attempt(user_id):
        session = SessionLocal()
        try:
            user = session.get(User, user_id)
            barrier.wait(timeout=10)
            join_queue(session, user, charger.id, str(uuid.uuid4()), utcnow())
            session.commit()
        finally:
            session.close()

    threads = [threading.Thread(target=attempt, args=(user.id,)) for user in (first, second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    with SessionLocal() as check:
        states = sorted(check.scalars(select(QueueEntry.state)).all())
        assert states == ["offered", "waiting"]


def test_expired_offer_promotes_the_next_driver_once(db):
    first = make_user(db, "expired@example.com")
    second = make_user(db, "next@example.com")
    charger = make_charger(db, capacity=1)
    now = utcnow()
    expired = QueueEntry(
        user_id=first.id,
        charger_id=charger.id,
        state="offered",
        joined_at=now - timedelta(minutes=20),
        offer_expires_at=now - timedelta(minutes=1),
        offer_round=1,
        idempotency_key="expired-key",
    )
    waiting = QueueEntry(
        user_id=second.id,
        charger_id=charger.id,
        state="waiting",
        joined_at=now - timedelta(minutes=10),
        offer_round=0,
        idempotency_key="waiting-key",
    )
    db.add_all([expired, waiting])
    db.commit()

    with pytest.raises(HTTPException) as caught:
        accept_offer(db, first, "accept-expired", now)
    assert caught.value.status_code == 409
    db.rollback()

    reconcile_charger(db, charger, now)
    db.commit()
    reconcile_charger(db, charger, now + timedelta(seconds=1))
    db.commit()

    db.refresh(expired)
    db.refresh(waiting)
    assert expired.state == "expired"
    assert waiting.state == "offered"
    notices = db.scalars(select(Notification).where(Notification.user_id == second.id, Notification.event_key.like("offer-made:%"))).all()
    assert len(list(notices)) == 1


def test_pause_and_resume_durations(db):
    user = make_user(db, "timer@example.com")
    charger = make_charger(db, capacity=1)
    db.commit()
    start = utcnow().replace(microsecond=0)
    session = direct_start(db, user, charger.id, "start-key", start)
    driver_action(db, user, session.id, "pause", "pause-1", start + timedelta(minutes=10))
    driver_action(db, user, session.id, "resume", "resume-1", start + timedelta(minutes=25))
    driver_action(db, user, session.id, "pause", "pause-2", start + timedelta(minutes=40))
    driver_action(db, user, session.id, "unplug", "unplug-1", start + timedelta(minutes=50))
    db.commit()
    db.refresh(session)
    seconds = session_seconds(session, list(session.intervals), start + timedelta(minutes=50))
    assert seconds == {"connected_seconds": 3000, "charging_seconds": 1500, "noncharging_seconds": 1500}
    with pytest.raises(HTTPException) as caught:
        driver_action(db, user, session.id, "resume", "resume-late", start + timedelta(minutes=60))
    assert caught.value.status_code == 409
