"""Meaningful PostgreSQL lifecycle and privacy checks for the approved brief."""
from datetime import date, timedelta
import threading
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.clock import utcnow
from app.db.models import ChargerPortType, ChargerReport, DepartureReport, HistoricalDemonstration, ManagerAssignment, Notification, Reminder, User
from app.services.coordination import create_report, deliver_due_reminders_once, public_departures, respond_report, schedule_reminder, set_departure
from app.services.queues import accept_offer, join_queue
from app.services.sessions import direct_start, driver_action
from tests.test_coordination import make_charger, make_user
from tests.conftest import csrf, register


def test_departure_is_anonymous_expires_and_never_releases_slot(db):
    first, second = make_user(db, "leaving@example.com"), make_user(db, "waiting@example.com")
    charger, now = make_charger(db), utcnow()
    session = direct_start(db, first, charger.id, "start-report", now)
    row = set_departure(db, first, session.id, now + timedelta(minutes=10), now)
    entry = join_queue(db, second, charger.id, "wait-report", now)
    db.commit()
    result = public_departures(db, charger.id, now)
    assert len(result) == 1 and set(result[0]) == {"expected_at", "reported_at"}
    assert public_departures(db, charger.id, now + timedelta(minutes=11)) == []
    assert session.unplugged_at is None and entry.state == "waiting"
    set_departure(db, first, session.id, None, now)
    db.commit()
    assert row.state == "retracted" and public_departures(db, charger.id, now) == []
    with pytest.raises(HTTPException):
        set_departure(db, second, session.id, now + timedelta(minutes=5), now)


def test_reminder_persists_delivers_once_without_browser_and_cancels_on_resume(db):
    driver, charger, now = make_user(db, "reminder@example.com"), make_charger(db), utcnow()
    session = direct_start(db, driver, charger.id, "reminder-start", now)
    driver_action(db, driver, session.id, "finish", "reminder-finish", now + timedelta(minutes=1))
    due = now + timedelta(minutes=2)
    row = schedule_reminder(db, driver, session.id, due, "reminder-request", now + timedelta(minutes=1))
    again = schedule_reminder(db, driver, session.id, due, "reminder-request", now + timedelta(minutes=1))
    assert row.id == again.id
    db.commit()
    assert deliver_due_reminders_once(due + timedelta(seconds=1)) == 1
    assert deliver_due_reminders_once(due + timedelta(seconds=2)) == 0
    db.expire_all()
    assert db.get(Reminder, row.id).state == "delivered"
    assert db.scalar(select(func.count()).select_from(Notification).where(Notification.event_key == f"return-reminder:{row.id}")) == 1
    snoozed = schedule_reminder(db, driver, session.id, now + timedelta(minutes=8), "snoozed-reminder", now + timedelta(minutes=3))
    driver_action(db, driver, session.id, "resume", "resume-finished", now + timedelta(minutes=4))
    db.commit()
    assert snoozed.state == "cancelled" and session.state == "charging"
    assert deliver_due_reminders_once(now + timedelta(minutes=9)) == 0


def test_unplug_cancels_reminder_and_departure_and_hands_over_once(db):
    driver, next_driver = make_user(db, "handover-a@example.com"), make_user(db, "handover-b@example.com")
    charger, now = make_charger(db), utcnow()
    session = direct_start(db, driver, charger.id, "handover-start", now)
    set_departure(db, driver, session.id, now + timedelta(minutes=20), now)
    driver_action(db, driver, session.id, "finish", "handover-finish", now + timedelta(minutes=1))
    reminder = schedule_reminder(db, driver, session.id, now + timedelta(minutes=10), "handover-reminder", now + timedelta(minutes=2))
    entry = join_queue(db, next_driver, charger.id, "handover-join", now + timedelta(minutes=2))
    driver_action(db, driver, session.id, "unplug", "handover-unplug", now + timedelta(minutes=3))
    driver_action(db, driver, session.id, "unplug", "handover-unplug", now + timedelta(minutes=3))
    db.commit()
    assert reminder.state == "cancelled"
    assert db.get(DepartureReport, session.id).state == "ended"
    assert entry.state == "offered"
    accepted = accept_offer(db, next_driver, "handover-accept", now + timedelta(minutes=4))
    assert accept_offer(db, next_driver, "handover-accept", now + timedelta(minutes=4)).id == accepted.id
    db.commit()
    assert db.scalar(select(func.count()).select_from(Notification).where(Notification.event_key.like(f"offer-made:{entry.id}:%"))) == 1


def test_private_help_report_is_scoped_idempotent_and_not_a_status_change(db):
    driver, other, manager = (make_user(db, email) for email in ("help@example.com", "other-help@example.com", "help-manager@example.com"))
    manager.role = "manager"
    charger, now = make_charger(db), utcnow()
    db.add(ManagerAssignment(manager_id=manager.id, charger_id=charger.id))
    db.flush()
    ticket = create_report(db, driver, charger.id, "not_working", "Screen is blank", "help-request", now)
    assert create_report(db, driver, charger.id, "not_working", "Screen is blank", "help-request", now).id == ticket.id
    assert charger.app_status == "available"
    other.role = "manager"
    with pytest.raises(HTTPException):
        respond_report(db, other, ticket.id, "resolved", "Checked this charger", now)
    response = respond_report(db, manager, ticket.id, "acknowledged", "We are checking the screen.", now)
    assert response.state == "acknowledged"
    respond_report(db, manager, ticket.id, "resolved", "The reported issue has been checked.", now + timedelta(minutes=1))
    db.commit()
    assert db.scalar(select(func.count()).select_from(ChargerReport)) == 1
    assert db.scalar(select(Notification.id).where(Notification.user_id == driver.id, Notification.event_key.like("help-response:%")))


def test_driver_manager_and_researcher_boundaries(http, db):
    account = register(http, "roles@example.com")
    user = db.get(User, UUID(account["id"]))
    for role in ("driver", "manager"):
        user.role = role
        db.commit()
        for path in ("/research/model", "/research/options", "/research/insights", "/research/demonstrations"):
            assert http.get("/api/v1" + path).status_code == 403
    user.role = "researcher"
    db.commit()
    assert http.get("/api/v1/research/model").status_code == 200
    assert http.get("/api/v1/conversations").status_code == 403
    assert http.get("/api/v1/manager/overview").status_code == 403
    assert http.post("/api/v1/queue/join", headers=csrf(http), json={"charger_id": str(make_charger(db).id), "idempotency_key": "researcher-no-join"}).status_code == 403


def test_departure_and_reminder_times_require_timezone_and_reasonable_future(db):
    driver, charger, now = make_user(db, "dates@example.com"), make_charger(db), utcnow()
    session = direct_start(db, driver, charger.id, "time-start", now)
    for when in (now - timedelta(seconds=1), now + timedelta(days=2), now.replace(tzinfo=None)):
        with pytest.raises(HTTPException) as error:
            set_departure(db, driver, session.id, when, now)
        assert error.value.status_code == 422
    with pytest.raises(HTTPException) as error:
        schedule_reminder(db, driver, session.id, now + timedelta(minutes=2), "not-finished", now)
    assert error.value.status_code == 409


def test_competing_accepts_create_only_one_session(db):
    from app.db.session import SessionLocal
    from app.db.models import ChargingSession
    driver, charger, now = make_user(db, "competing@example.com"), make_charger(db), utcnow()
    join_queue(db, driver, charger.id, "competing-join", now)
    db.commit()
    barrier, results = threading.Barrier(2), []
    def attempt(index):
        with SessionLocal() as transaction:
            person = transaction.get(User, driver.id)
            barrier.wait(timeout=10)
            try:
                accept_offer(transaction, person, f"competing-accept-{index}", now + timedelta(seconds=1))
                transaction.commit(); results.append(201)
            except HTTPException as error:
                transaction.rollback(); results.append(error.status_code)
    workers = [threading.Thread(target=attempt, args=(index,)) for index in range(2)]
    for worker in workers: worker.start()
    for worker in workers: worker.join(timeout=15)
    assert not any(worker.is_alive() for worker in workers)
    assert sorted(results) == [201, 409]
    assert db.scalar(select(func.count()).select_from(ChargingSession)) == 1


def test_two_reminder_workers_deliver_once(db):
    driver, charger, now = make_user(db, "two-workers@example.com"), make_charger(db), utcnow()
    session = direct_start(db, driver, charger.id, "worker-start", now)
    driver_action(db, driver, session.id, "finish", "worker-finish", now + timedelta(seconds=1))
    row = schedule_reminder(db, driver, session.id, now + timedelta(seconds=3), "worker-reminder", now + timedelta(seconds=1))
    db.commit()
    barrier, results = threading.Barrier(2), []
    def work():
        barrier.wait(timeout=10)
        results.append(deliver_due_reminders_once(now + timedelta(seconds=4)))
    workers = [threading.Thread(target=work) for _ in range(2)]
    for worker in workers: worker.start()
    for worker in workers: worker.join(timeout=15)
    assert not any(worker.is_alive() for worker in workers)
    assert sorted(results) == [0, 1]
    assert db.scalar(select(func.count()).select_from(Notification).where(Notification.event_key == f"return-reminder:{row.id}")) == 1


def test_concurrent_read_markers_are_atomic_and_never_move_backwards(db):
    from app.db.models import Conversation, ReadMarker
    from app.db.session import SessionLocal
    from app.services.messages import mark_read
    driver, charger, now = make_user(db, "read-race@example.com"), make_charger(db), utcnow()
    thread = Conversation(driver_id=driver.id, charger_id=charger.id, created_at=now)
    db.add(thread); db.commit()
    barrier, errors = threading.Barrier(2), []
    def update(seconds):
        try:
            with SessionLocal() as transaction:
                barrier.wait(timeout=10)
                mark_read(transaction, thread.id, driver.id, now + timedelta(seconds=seconds))
                transaction.commit()
        except Exception as error: errors.append(str(error))
    workers = [threading.Thread(target=update, args=(seconds,)) for seconds in (1, 2)]
    for worker in workers: worker.start()
    for worker in workers: worker.join(timeout=15)
    assert not any(worker.is_alive() for worker in workers)
    assert errors == []
    assert db.get(ReadMarker, (thread.id, driver.id)).last_read_at == now + timedelta(seconds=2)


def test_assigned_manager_timezone_status_and_close_notifications(db):
    from app.services.manager import update_charger
    from app.services.sessions import manager_close
    driver, manager = make_user(db, "status-driver@example.com"), make_user(db, "status-manager@example.com")
    manager.role = "manager"
    charger, now = make_charger(db), utcnow()
    db.add(ManagerAssignment(manager_id=manager.id, charger_id=charger.id)); db.flush()
    session = direct_start(db, driver, charger.id, "status-start", now)
    update_charger(db, manager, charger.id, display_name=None, app_status="offline", service_capacity=None, capacity_supplied=False, port_types_to_add=None, timezone_name="Africa/Johannesburg")
    db.commit()
    assert charger.timezone_name == "Africa/Johannesburg"
    assert db.scalar(select(Notification.id).where(Notification.user_id == driver.id, Notification.event_key.like("active-status:%")))
    manager_close(db, manager, charger.id, session.id, "Demonstration session was abandoned", "status-close", now + timedelta(minutes=1))
    manager_close(db, manager, charger.id, session.id, "Demonstration session was abandoned", "status-close", now + timedelta(minutes=1))
    db.commit()
    assert db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == driver.id, Notification.event_key.like("manager-close:%"))) == 1
    with pytest.raises(HTTPException) as error:
        update_charger(db, manager, charger.id, display_name=None, app_status=None, service_capacity=None, capacity_supplied=False, port_types_to_add=None, timezone_name="Not/A_Real_Timezone")
    assert error.value.status_code == 422
