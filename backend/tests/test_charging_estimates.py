"""Real calculation, privacy, stale-edit and durable delivery checks."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.clock import utcnow
from app.db.models import ChargeEstimate, ChargingSession, Notification, Vehicle, User
from app.db.session import SessionLocal
from app.schemas import ChargeEstimateIn
from app.services import charging_estimates as service
from app.services.queues import join_queue
from app.services.sessions import direct_start, driver_action
from tests.conftest import csrf, register
from tests.test_coordination import make_charger, make_user


def plan(**overrides):
    return ChargeEstimateIn(**{"vehicle_label": "Example 60 kWh car", "battery_capacity_kwh": 60,
        "current_percent": 40, "target_percent": 80, "average_power_kw": 12, **overrides})


def scene(db):
    owner, waiter, outsider = [make_user(db, f"{name}@example.com") for name in ("estimate-owner", "estimate-waiter", "estimate-outsider")]
    charger, now = make_charger(db), utcnow()
    session = direct_start(db, owner, charger.id, "estimate-start", now)
    join_queue(db, waiter, charger.id, "estimate-join", now)
    db.commit()
    return owner, waiter, outsider, charger, session, now


@pytest.mark.parametrize("capacity,current,target,power,limit,seconds", [
    (60,40,80,12,None,7200), (90,40,80,12,None,10800), (60,40,80,12,6,14400),
    (60,80,80,12,None,0), (60,0,100,12,None,18000),
])
def test_energy_and_power_calculation(capacity,current,target,power,limit,seconds):
    result = service.calculate(capacity,current,target,power,limit)
    assert result["duration_seconds"] == seconds
    assert result["energy_needed_kwh"] == capacity*(target-current)/100


def test_invalid_and_nonfinite_inputs_rejected():
    for args in ({"average_power_kw": 0}, {"battery_capacity_kwh": float("nan")}, {"current_percent": -1}, {"target_percent":101}):
        with pytest.raises(ValueError): plan(**args)
    with pytest.raises(HTTPException): service.calculate(60,80,40,12)
    with pytest.raises(HTTPException): service.calculate(500,0,100,0.01)


def test_owned_vehicle_capacity_and_ac_dc_limits(db):
    owner, _, outsider, _, _, now = scene(db)
    vehicle = Vehicle(user_id=owner.id,nickname="My car",model_name="Exact version",battery_capacity_kwh=72,max_ac_kw=7.2,max_dc_kw=100)
    db.add(vehicle);db.flush()
    result = service.preview(db, owner, plan(vehicle_id=vehicle.id,battery_capacity_kwh=60,average_power_kw=50),now)
    assert result["battery_capacity_kwh"] == 72 and result["effective_power_kw"] == 7.2
    assert service.preview(db,owner,plan(vehicle_id=vehicle.id,charging_kind="DC",average_power_kw=50),now)["effective_power_kw"] == 50
    with pytest.raises(HTTPException) as caught: service.preview(db, outsider, plan(vehicle_id=vehicle.id),now)
    assert caught.value.status_code == 404


def test_preview_is_read_only_and_start_attaches_atomically(http,db):
    user = register(http,"estimate-api@example.com")
    charger=make_charger(db);db.commit()
    body=plan().model_dump(mode="json")
    preview=http.post("/api/v1/charging-estimates/preview",json=body,headers=csrf(http))
    assert preview.status_code == 200 and preview.json()["estimate"]["duration_seconds"] == 7200
    assert db.scalar(select(func.count()).select_from(ChargeEstimate)) == 0
    assert db.scalar(select(func.count()).select_from(ChargingSession)) == 0
    start={"charger_id":str(charger.id),"idempotency_key":"start-with-estimate","charge_estimate":{**body,"target_percent":20}}
    assert http.post("/api/v1/sessions",json=start,headers=csrf(http)).status_code == 422
    assert db.scalar(select(func.count()).select_from(ChargingSession)) == 0
    start["charge_estimate"]=body
    first=http.post("/api/v1/sessions",json=start,headers=csrf(http));assert first.status_code == 201
    second=http.post("/api/v1/sessions",json=start,headers=csrf(http));assert second.status_code == 201
    assert first.json()["session"]["id"] == second.json()["session"]["id"]
    assert http.get(f"/api/v1/chargers/{charger.id}").json()["app_status"] == "occupied"
    row=db.scalar(select(ChargeEstimate));session=db.get(ChargingSession,row.session_id)
    assert row.anchor_at == session.plugged_in_at
    assert row.estimated_target_at-row.anchor_at == timedelta(hours=2)
    assert db.scalar(select(func.count()).select_from(ChargeEstimate)) == 1
    assert str(session.user_id) == user["id"]


def test_updates_are_versioned_idempotent_and_cancel_old_work(db):
    owner,_,_,_,session,now=scene(db)
    old=service.save(db,owner,session.id,plan(current_percent=79),"estimate-one",0,now);db.commit()
    new=service.save(db,owner,session.id,plan(current_percent=40),"estimate-two",1,now+timedelta(minutes=1));db.commit()
    assert not old.is_active and new.is_active and new.version == 2
    assert service.save(db,owner,session.id,plan(),"estimate-one",0,now).id == old.id
    assert new.anchor_at == now+timedelta(minutes=1)
    with pytest.raises(HTTPException) as caught: service.save(db,owner,session.id,plan(),"stale-estimate",1,now)
    assert caught.value.status_code == 409
    db.rollback()
    assert service.deliver_due_once(now+timedelta(minutes=6)) == 0


def test_anonymous_station_summary_omits_vehicle_and_identity(db):
    owner,_,_,charger,session,now=scene(db)
    service.save(db,owner,session.id,plan(),"anonymous-estimate",0,now);db.commit()
    result=service.station_summary(db,charger.id,now)
    assert result["connected_count"] == 1 and result["unestimated_count"] == 0
    assert set(result["items"][0]) == {"stage","estimated_target_at","is_estimate"}
    assert "vehicle" not in str(result) and str(owner.id) not in str(result) and str(session.id) not in str(result)


def test_durable_near_target_alerts_and_unplug_handover(db):
    owner,waiter,outsider,charger,session,now=scene(db)
    row=service.save(db,owner,session.id,plan(current_percent=79),"near-target-estimate",0,now);db.commit()
    assert service.deliver_due_once(now+timedelta(seconds=1)) == 2
    assert service.deliver_due_once(now+timedelta(seconds=2)) == 0
    assert service.deliver_due_once(row.estimated_target_at+timedelta(seconds=1)) == 2
    assert service.deliver_due_once(row.estimated_target_at+timedelta(seconds=2)) == 0
    db.expire_all()
    notes=list(db.scalars(select(Notification).where(Notification.event_key.like("charge-%"))))
    assert len(notes) == 4 and {n.user_id for n in notes} == {owner.id,waiter.id}
    assert all(n.user_id != outsider.id for n in notes)
    assert all("estimated" in n.title.lower() for n in notes)
    assert session.unplugged_at is None
    driver_action(db,owner,session.id,"finish","estimate-finished",now+timedelta(minutes=5));db.commit()
    summary=service.station_summary(db,charger.id,now+timedelta(minutes=5))
    assert summary["items"][0]["stage"] == "driver_reported_finished"
    assert service.deliver_due_once(now+timedelta(hours=3)) == 0
    from app.db.models import QueueEntry
    assert db.scalar(select(QueueEntry).where(QueueEntry.user_id==waiter.id)).state == "waiting"
    driver_action(db,owner,session.id,"unplug","estimate-unplugged",now+timedelta(minutes=6));db.commit()
    assert db.scalar(select(QueueEntry).where(QueueEntry.user_id==waiter.id)).state == "offered"
    assert service.deliver_due_once(now+timedelta(hours=4)) == 0


def test_catchup_skips_stale_almost_full_notice(db):
    owner,_,_,_,session,now=scene(db)
    row=service.save(db,owner,session.id,plan(current_percent=79),"wake-estimate",0,now);db.commit()
    assert service.deliver_due_once(row.estimated_target_at+timedelta(hours=1)) == 2
    assert db.scalar(select(func.count()).select_from(Notification).where(Notification.event_key.like("charge-near:%"))) == 0
    assert service.deliver_due_once(row.estimated_target_at+timedelta(hours=2)) == 0


def test_multiple_workers_deliver_once(db):
    owner,_,_,_,session,now=scene(db)
    service.save(db,owner,session.id,plan(current_percent=79),"parallel-workers",0,now);db.commit()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:service.deliver_due_once(now+timedelta(seconds=1)),range(2)))
    assert sum(results) == 2


def test_competing_edits_preserve_one_current_revision(db):
    owner,_,_,_,session,now=scene(db)
    service.save(db,owner,session.id,plan(),"first-edit",0,now);db.commit()
    user_id,session_id=owner.id,session.id
    def update(index):
        with SessionLocal() as connection:
            try:
                service.save(connection,connection.get(User,user_id),session_id,plan(current_percent=45+index),f"competing-{index}",1,now+timedelta(minutes=1))
                connection.commit();return 200
            except HTTPException as error:
                connection.rollback();return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(update,range(2)))
    assert sorted(results) == [200,409]
    assert db.scalar(select(func.count()).select_from(ChargeEstimate).where(ChargeEstimate.is_active.is_(True))) == 1


def test_estimate_api_ownership_removal_and_vehicle_validation(http,db):
    register(http,"estimate-permission@example.com")
    v=http.post("/api/v1/me/vehicles",json={"nickname":"Car","battery_capacity_kwh":60,"max_ac_kw":7.2},headers=csrf(http))
    assert v.status_code==201 and v.json()["battery_capacity_kwh"]==60
    assert http.post("/api/v1/me/vehicles",json={"nickname":"Bad","battery_capacity_kwh":-5},headers=csrf(http)).status_code==422
    charger=make_charger(db);db.commit()
    created=http.post("/api/v1/sessions",json={"charger_id":str(charger.id),"idempotency_key":"owner-start-estimate"},headers=csrf(http)).json()["session"]
    sid=created["id"]
    first=http.post(f"/api/v1/sessions/{sid}/charge-estimate",json={**plan().model_dump(mode="json"),"expected_version":0,"idempotency_key":"owner-save-estimate"},headers=csrf(http))
    assert first.status_code==200
    assert http.delete(f"/api/v1/sessions/{sid}/charge-estimate?version=2",headers=csrf(http)).status_code==409
    assert http.delete(f"/api/v1/sessions/{sid}/charge-estimate?version=1",headers=csrf(http)).status_code==204
    assert http.get(f"/api/v1/sessions/{sid}/charge-estimate").json()["estimate"] is None
    register(http,"estimate-other@example.com")
    assert http.get(f"/api/v1/sessions/{sid}/charge-estimate").status_code==404
    assert http.post(f"/api/v1/sessions/{sid}/charge-estimate",json={**plan().model_dump(mode="json"),"expected_version":1,"idempotency_key":"other-save-estimate"},headers=csrf(http)).status_code==404
