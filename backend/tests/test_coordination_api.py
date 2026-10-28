"""Privacy and atomic switching through real PostgreSQL request transactions."""
from uuid import UUID
from sqlalchemy import select
from app.db.models import ChargerReport, QueueEntry, User
from tests.conftest import csrf, register
from tests.test_coordination import make_charger, make_user
from app.services.queues import join_queue
from app.core.clock import utcnow


def test_atomic_switch_requires_confirmation_preserves_failed_participation_and_replays(http, db):
    account = register(http, "switch@example.com")
    user = db.get(User, UUID(account["id"]))
    first, second = make_charger(db), make_charger(db)
    old = join_queue(db, user, first.id, "original-queue", utcnow())
    db.commit()
    body = {"charger_id":str(second.id),"expected_charger_id":str(first.id),"idempotency_key":"switch-request"}
    assert http.post("/api/v1/queue/switch", headers=csrf(http), json=body).status_code == 422
    body["confirm_leave"] = True
    second.app_status = "offline"
    db.commit()
    assert http.post("/api/v1/queue/switch", headers=csrf(http), json=body).status_code == 409
    db.refresh(old)
    assert old.state == "offered"
    second.app_status = "available"
    db.commit()
    response = http.post("/api/v1/queue/switch", headers=csrf(http), json=body)
    assert response.status_code == 200, response.text
    assert http.post("/api/v1/queue/switch", headers=csrf(http), json=body).json() == response.json()
    db.refresh(old)
    assert old.state == "left"
    assert len(db.scalars(select(QueueEntry).where(QueueEntry.user_id == user.id,QueueEntry.state.in_(("waiting","offered")))).all()) == 1


def test_private_report_cross_user_and_unassigned_manager_denied(http, db):
    account = register(http, "report-owner@example.com")
    owner_id = account["id"]
    charger = make_charger(db)
    db.commit()
    response = http.post(f"/api/v1/chargers/{charger.id}/reports", headers=csrf(http),json={"category":"access_blocked","details":"Delivery vehicle blocks access.","idempotency_key":"private-report"})
    assert response.status_code == 201
    report_id=response.json()["id"]
    http.cookies.clear()
    other=register(http,"report-other@example.com")
    assert http.get(f"/api/v1/chargers/{charger.id}/reports").json()["items"] == []
    person=db.get(User,UUID(other["id"]))
    for role in ("manager","researcher"):
        person.role=role; db.commit()
        result=http.get(f"/api/v1/manager/chargers/{charger.id}/reports")
        assert result.status_code in (403,404)
        result=http.patch(f"/api/v1/manager/reports/{report_id}",headers=csrf(http),json={"state":"resolved","response":"Not authorised"})
        assert result.status_code in (403,404)
    assert str(db.get(ChargerReport,UUID(report_id)).reporter_id)==owner_id


def test_researcher_cannot_choose_a_real_driver_for_demo(http, db):
    examiner=register(http,"strict-examiner@example.com")
    db.get(User,UUID(examiner["id"])).role="researcher"
    driver=make_user(db,"real-participant@example.com")
    db.commit()
    response=http.post("/api/v1/research/demonstrations",headers=csrf(http),json={"driver_id":str(driver.id),"station_key":"PALO ALTO CA / HAMILTON #2","port_type":"Level 1","arrival_date":"2020-06-15","arrival_time":"22:00"})
    assert response.status_code==403
