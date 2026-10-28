"""The walkthrough must be usable, consistent and unable to reset real users."""
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.clock import utcnow
from app.core.security import verify_password
from app.db.models import Charger, ChargingSession, Favourite, Notification, QueueEntry, User
from app.services.queues import queue_position
from app.services.sessions import session_seconds
from app.showcase import PEOPLE, email, identity, populate, seed_showcase


def passwords():
    return {email(key): f"{key}-local-check-only!" for key in PEOPLE}


def test_showcase_has_five_charging_eight_fifo_waiting_and_consistent_sessions(db):
    now, credentials = utcnow(), passwords()
    assert populate(db, credentials, now)
    db.commit()
    hub = identity("charger", "rosebank")
    active = db.scalars(select(ChargingSession).where(ChargingSession.charger_id == hub, ChargingSession.unplugged_at.is_(None))).all()
    assert len(active) == 5 and {row.state for row in active} == {"charging"}
    assert db.get(Charger, hub).app_status == "occupied"
    assert db.get(Charger, identity("charger", "sandton")).app_status == "occupied"
    waiting = db.scalars(select(QueueEntry).where(QueueEntry.charger_id == hub, QueueEntry.state == "waiting").order_by(QueueEntry.joined_at)).all()
    assert len(waiting) == 8
    assert [queue_position(db, row) for row in waiting] == list(range(1, 9))
    assert len(db.scalars(select(User)).all()) == 28
    for key in PEOPLE:
        user = db.get(User, identity("user", key))
        assert user.is_demonstration and "demo" not in user.email
        assert verify_password(credentials[user.email], user.password_hash)
    for session in db.scalars(select(ChargingSession)):
        seconds = session_seconds(session, session.intervals, now)
        assert seconds["connected_seconds"] == seconds["charging_seconds"] + seconds["noncharging_seconds"]
    assert db.scalar(select(func.count()).select_from(ChargingSession).where(ChargingSession.user_id == identity("user", "lucas.meyer"))) == 23
    mia = db.scalar(select(QueueEntry).where(QueueEntry.user_id == identity("user", "mia.johnson")))
    assert mia.state == "offered" and mia.offer_expires_at > now
    missed = db.scalar(select(QueueEntry).where(QueueEntry.user_id == identity("user", "benjamin.nkosi")))
    assert missed.state == "expired"
    reminder = db.scalar(select(Notification).where(Notification.user_id == identity("user", "sarah.vandermerwe"), Notification.title == "Waiting driver reminder"))
    assert reminder.destination == f"/app/manage/chargers/{hub}"


def test_showcase_keep_progress_then_reset_preserves_unrelated_records(db):
    unrelated = User(email="existing-owner@example.com", display_name="Existing Owner", role="driver", password_hash="untouched")
    db.add(unrelated)
    db.commit()
    unrelated_id, now = unrelated.id, utcnow()
    credentials = passwords()
    populate(db, credentials, now)
    db.commit()
    saved = db.scalar(select(Favourite).where(Favourite.user_id == identity("user", "aisha.khan")))
    db.delete(saved)
    db.commit()
    assert not populate(db, credentials, now + timedelta(minutes=1))
    assert db.get(Favourite, (saved.user_id, saved.charger_id)) is None
    assert populate(db, credentials, now + timedelta(minutes=2), reset=True)
    db.commit()
    assert db.get(Favourite, (saved.user_id, saved.charger_id)) is not None
    existing = db.get(User, unrelated_id)
    assert existing.email == "existing-owner@example.com" and existing.password_hash == "untouched"
    assert db.scalar(select(func.count()).select_from(User)) == 29
    assert db.scalar(select(func.count()).select_from(QueueEntry).where(QueueEntry.state == "waiting")) == 8


def test_showcase_refuses_account_collision_before_any_changes(db):
    db.add(User(email=email("thabo.mokoena"), display_name="Existing real person", password_hash="keep-me", role="driver", is_demonstration=False))
    db.commit()
    with pytest.raises(ValueError, match="unrelated account"):
        populate(db, passwords(), utcnow(), reset=True)
    db.rollback()
    assert db.scalar(select(func.count()).select_from(User)) == 1
    assert db.scalar(select(func.count()).select_from(Charger)) == 0


def test_showcase_refuses_reset_after_unrelated_driver_uses_its_station(db):
    populate(db, passwords(), utcnow())
    outsider = User(email="outside@example.com", display_name="Outside Driver", role="driver", password_hash="keep")
    db.add(outsider)
    db.flush()
    db.add(Favourite(user_id=outsider.id, charger_id=identity("charger", "rosebank")))
    from app.services.queues import join_queue
    join_queue(db, outsider, identity("charger", "rosebank"), "outside-join", utcnow())
    db.commit()
    with pytest.raises(ValueError, match="unrelated records"):
        populate(db, passwords(), utcnow(), reset=True)
    db.rollback()
    assert db.scalar(select(QueueEntry.id).where(QueueEntry.user_id == outsider.id, QueueEntry.state == "waiting"))
    assert db.get(Favourite, (outsider.id, identity("charger", "rosebank")))


def test_showcase_cannot_run_in_production_or_create_credential_file(tmp_path, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "environment", "production")
    with pytest.raises(SystemExit, match="production"):
        seed_showcase(directory=tmp_path)
    assert list(tmp_path.iterdir()) == []
