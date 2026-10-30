"""Administrator visibility, meaningful filters and reported-duration summaries."""
from datetime import timedelta
from uuid import UUID

from app.core.clock import utcnow
from app.db.models import ChargerReport, Conversation, Favourite, ManagerAssignment, Message, User, Vehicle
from app.services import administration
from app.services.queues import join_queue
from app.services.sessions import direct_start, driver_action
from tests.conftest import csrf, register
from tests.test_coordination import make_charger, make_user


def test_admin_access_requires_explicit_grant_and_public_forms_cannot_grant_it(http, db):
    for extra in ({"role": "manager"}, {"is_admin": True}):
        assert http.post("/api/v1/auth/register", headers=csrf(http), json={
            "email": "escalate@example.com", "display_name": "Attempt", "password": "correct-horse-battery", **extra}).status_code == 422
    account = register(http, "operator@example.com")
    person = db.get(User, UUID(account["id"]))
    driver = make_user(db, "private@example.com")
    db.commit()
    for role, flag in (("driver", False), ("researcher", True), ("manager", False)):
        person.role, person.is_admin = role, flag
        db.commit()
        assert http.get("/api/v1/admin/drivers").status_code == 403
        assert http.get(f"/api/v1/admin/drivers/{driver.id}").status_code == 403
    person.role, person.is_admin = "manager", True
    db.commit()
    assert http.get("/api/v1/auth/me").json()["user"]["is_admin"] is True
    result = http.get("/api/v1/admin/drivers")
    assert result.status_code == 200, result.text
    assert result.json()["total"] == 1
    assert "password" not in result.text and "token" not in result.text and "probability" not in result.text
    assert http.get("/api/v1/admin/drivers", params={"days": "7"}).status_code == 200
    assert http.get("/api/v1/admin/drivers", params={"days": "8"}).status_code == 422
    assert http.get("/api/v1/admin/drivers", params={"status": "invented"}).status_code == 422
    assert http.get(f"/api/v1/admin/drivers/{person.id}").status_code == 404
    assert http.get("/api/v1/research/model").status_code == 403


def test_real_activity_filters_pagination_and_session_window(db):
    admin = make_user(db, "admin@example.com"); admin.role = "manager"; admin.is_admin = True
    charger, other_charger = make_charger(db), make_charger(db)
    db.add(ManagerAssignment(manager_id=admin.id, charger_id=charger.id))
    owner, waiter, idle, old_driver = [make_user(db, value + "@example.com") for value in ("owner", "waiter", "idle", "old")]
    now = utcnow()
    old = direct_start(db, old_driver, other_charger.id, "old-session", now - timedelta(days=40))
    driver_action(db, old_driver, old.id, "unplug", "old-unplug", now - timedelta(days=40) + timedelta(hours=1))
    ended = direct_start(db, owner, charger.id, "ended-session", now - timedelta(days=2, hours=2))
    driver_action(db, owner, ended.id, "finish", "finished-report", now - timedelta(days=2, minutes=30))
    driver_action(db, owner, ended.id, "unplug", "unplugged-report", now - timedelta(days=2))
    live = direct_start(db, owner, charger.id, "active-session", now - timedelta(minutes=10))
    join_queue(db, waiter, charger.id, "waiting-person", now - timedelta(minutes=5))
    db.add(Vehicle(user_id=owner.id, nickname="Personal car", battery_capacity_kwh=60))
    db.add(Favourite(user_id=owner.id, charger_id=charger.id))
    db.add(ChargerReport(charger_id=charger.id, reporter_id=waiter.id, category="access_blocked", state="open", details="Access blocked by a delivery.", idempotency_key="blocked-report"))
    conversation = Conversation(charger_id=charger.id, driver_id=owner.id); db.add(conversation); db.flush()
    db.add(Message(conversation_id=conversation.id, sender_id=owner.id, body="Please help", client_request_id="admin-private-message"))
    db.flush()
    data = administration.directory(db, admin, days=7)
    assert data["total"] == 4
    assert data["summary"]["charging"] == 1 and data["summary"]["waiting"] == 1
    assert data["summary"]["completed_sessions"] == 1
    assert data["summary"]["noncharging_seconds"] == 1800
    assert data["summary"]["open_reports"] == 1 and data["summary"]["unread_messages"] == 1
    assert administration.directory(db, admin, status="waiting")["items"][0]["id"] == waiter.id
    assert administration.directory(db, admin, status="has_favourites")["total"] == 1
    assert administration.directory(db, admin, status="no_vehicle")["total"] == 3
    assert administration.directory(db, admin, needs_attention=True)["total"] == 2
    assert administration.directory(db, admin, q="OWNER@EXAMPLE")["total"] == 1
    assert administration.directory(db, admin, q="%")["total"] == 0  # Literal search, not wildcard expansion.
    assert administration.directory(db, admin, charger_id=charger.id)["total"] == 2
    assert administration.directory(db, admin, status="idle")["total"] == 2
    first = administration.directory(db, admin, limit=2)
    second = administration.directory(db, admin, limit=2, offset=2)
    assert first["total"] == second["total"] == 4
    assert len({row["id"] for row in first["items"] + second["items"]}) == 4
    detail = administration.driver_detail(db, admin, owner.id, days=7, limit=1)
    assert detail["sessions"]["total"] == 2 and len(detail["sessions"]["items"]) == 1
    assert detail["session_summary"]["noncharging_seconds"] == 1800
    assert detail["vehicles"][0]["battery_capacity_kwh"] == 60
    assert detail["favourites"]["total"] == 1 and detail["conversations"]["items"][0]["can_manage"]
    assert administration.driver_detail(db, admin, old_driver.id, days=7)["sessions"]["total"] == 0
    assert administration.driver_detail(db, admin, old_driver.id)["sessions"]["total"] == 1
    # Oversight alone does not grant private messaging or charger actions.
    db.query(ManagerAssignment).filter_by(manager_id=admin.id).delete(); db.flush()
    assert not administration.driver_detail(db, admin, owner.id)["conversations"]["items"][0]["can_manage"]
    assert administration.directory(db, admin)["summary"]["unread_messages"] == 0
    driver_action(db, owner, live.id, "finish", "live-finish", now)
    assert administration.directory(db, admin, status="finished_plugged")["total"] == 1
