"""Consent, rescheduling, power bounds, historical isolation and recovery."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from math import ceil
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.clock import utcnow
from app.db.models import AssistantReminder, ChargeEstimate, ChargerPortType, ChargingSession, ManagerAssignment, Notification, User, Vehicle
from app.schemas import AssistantReminderIn, ChargeComparisonIn, PortPowerIn
from app.services import assistant, charging_estimates
from app.services.manager import update_charger
from app.services.sessions import driver_action
from tests.conftest import csrf, register
from tests.test_charging_estimates import plan, scene
from tests.test_coordination import make_charger, make_user


def choice(enabled=True, version=0, lead=10):
    return AssistantReminderIn(enabled=enabled, expected_version=version, lead_minutes=lead)


@pytest.mark.parametrize("current,target,minutes,gain,end,unused", [(40,80,30,6,50,0),(79,80,30,.6,80,1620),(80,80,30,0,80,1800)])
def test_time_budget_is_bounded_by_target(db,current,target,minutes,gain,end,unused):
    owner=make_user(db,"budget@example.com")
    estimate=charging_estimates.preview(db,owner,plan(current_percent=current,target_percent=target),utcnow())
    budget=charging_estimates.time_budget(estimate,minutes)
    assert budget["energy_gain_kwh"]==gain and budget["estimated_end_percent"]==end
    assert budget["unused_seconds"]==unused
    assert db.scalar(select(func.count()).select_from(ChargingSession))==0


def test_manager_port_and_vehicle_caps_and_unknown_comparison(db):
    owner=make_user(db,"comparison@example.com")
    a,b,unknown=make_charger(db),make_charger(db),make_charger(db)
    for charger,power in [(a,7),(b,22)]:
        db.add(ChargerPortType(charger_id=charger.id,name="Type 2",origin="manager",power_kw=power,charging_kind="AC"))
    vehicle=Vehicle(user_id=owner.id,nickname="Car",battery_capacity_kwh=60,max_ac_kw=11,max_dc_kw=50)
    db.add(vehicle);db.flush()
    body=plan(vehicle_id=vehicle.id,average_power_kw=30)
    values=assistant.compare(db,owner,ChargeComparisonIn(plan=body,charger_ids=[a.id,b.id,unknown.id]),utcnow())["items"]
    assert values[0]["estimate"]["effective_power_kw"]==7
    assert values[1]["estimate"]["effective_power_kw"]==11
    assert values[0]["estimate"]["duration_seconds"]==ceil(24/7*3600)
    assert not values[2]["available"] and "power" in values[2]["reason"]
    with pytest.raises(HTTPException):
        charging_estimates.preview(db,owner,body.model_copy(update={"charger_id":a.id,"port_type":"Type 2","charging_kind":"DC"}),utcnow())
    foreign=make_user(db,"foreign-comparison@example.com")
    with pytest.raises(HTTPException) as err:
        assistant.compare(db,foreign,ChargeComparisonIn(plan=body,charger_ids=[unknown.id]),utcnow())
    assert err.value.status_code==404


def test_power_edits_require_assignment_and_complete_pair(db):
    manager=make_user(db,"power-manager@example.com");manager.role="manager"
    charger=make_charger(db)
    db.add(ChargerPortType(charger_id=charger.id,name="Type 2",origin="historical"));db.flush()
    args=dict(display_name=None,app_status=None,service_capacity=None,capacity_supplied=False,port_types_to_add=None)
    with pytest.raises(HTTPException):update_charger(db,manager,charger.id,**args,port_power_updates=[PortPowerIn(name="Type 2",power_kw=7,charging_kind="AC")])
    db.add(ManagerAssignment(manager_id=manager.id,charger_id=charger.id));db.flush()
    with pytest.raises(HTTPException):update_charger(db,manager,charger.id,**args,port_power_updates=[PortPowerIn(name="Type 2",power_kw=7)])
    update_charger(db,manager,charger.id,**args,port_power_updates=[PortPowerIn(name="Type 2",power_kw=7,charging_kind="AC")])
    port=db.scalar(select(ChargerPortType));assert port.power_kw==7 and port.origin=="historical" and port.power_updated_at
    update_charger(db,manager,charger.id,**args,port_power_updates=[PortPowerIn(name="Type 2")])
    assert port.power_kw is None and port.charging_kind is None


def test_explicit_consent_retry_and_ownership(db):
    owner,_,other,_,session,now=scene(db)
    assert assistant.get_reminder(db,owner,session.id)["enabled"] is False
    assert db.scalar(select(func.count()).select_from(AssistantReminder))==0
    with pytest.raises(HTTPException):assistant.set_reminder(db,owner,session.id,choice(),now)
    charging_estimates.save(db,owner,session.id,plan(),"initial-estimate",0,now)
    value=assistant.set_reminder(db,owner,session.id,choice(),now)
    assert value["enabled"] and value["due_at"]==now+timedelta(minutes=110)
    assert assistant.set_reminder(db,owner,session.id,choice(),now)["version"]==value["version"]
    with pytest.raises(HTTPException):assistant.get_reminder(db,other,session.id)
    with pytest.raises(HTTPException):assistant.set_reminder(db,other,session.id,choice(),now)
    with pytest.raises(HTTPException):assistant.set_reminder(db,owner,session.id,choice(False),now)


def test_battery_revision_reschedules_and_dismissal_stays_off(db):
    owner,_,_,_,session,now=scene(db)
    charging_estimates.save(db,owner,session.id,plan(),"estimate-a",0,now)
    first=assistant.set_reminder(db,owner,session.id,choice(),now)
    charging_estimates.save(db,owner,session.id,plan(current_percent=50),"estimate-b",1,now+timedelta(minutes=20))
    db.flush()
    second=assistant.get_reminder(db,owner,session.id)
    assert second["due_at"]==now+timedelta(minutes=100)
    assert second["version"]>first["version"] and second["estimate_version"]==2
    assistant.set_reminder(db,owner,session.id,choice(False,second["version"]),now+timedelta(minutes=21))
    charging_estimates.save(db,owner,session.id,plan(current_percent=60),"estimate-c",2,now+timedelta(minutes=30))
    assert not assistant.get_reminder(db,owner,session.id)["enabled"]


def test_parallel_worker_and_wake_catchup_notify_owner_only(db):
    owner,waiter,_,_,session,now=scene(db)
    charging_estimates.save(db,owner,session.id,plan(),"estimate-a",0,now)
    row=assistant.set_reminder(db,owner,session.id,choice(),now)
    db.commit()
    moment=row["due_at"]+timedelta(minutes=15)
    with ThreadPoolExecutor(max_workers=2) as pool:counts=list(pool.map(lambda _:assistant.deliver_due_once(moment),range(2)))
    assert sum(counts)==1 and assistant.deliver_due_once(moment+timedelta(hours=1))==0
    db.expire_all()
    notes=list(db.scalars(select(Notification).where(Notification.event_key.like("assistant-return:%"))))
    assert len(notes)==1 and notes[0].user_id==owner.id
    assert db.get(ChargingSession,session.id).state=="charging"
    assert not db.scalar(select(Notification).where(Notification.user_id==waiter.id,Notification.event_key.like("assistant-return:%")))


@pytest.mark.parametrize("action",["finish","unplug","pause"])
def test_completion_and_legacy_pause_cancel_optional_reminder(db,action):
    owner,_,_,_,session,now=scene(db)
    charging_estimates.save(db,owner,session.id,plan(),"estimate-a",0,now)
    assistant.set_reminder(db,owner,session.id,choice(),now)
    driver_action(db,owner,session.id,action,"cancel-"+action,now+timedelta(minutes=5));db.commit()
    assert not assistant.get_reminder(db,owner,session.id)["enabled"]
    assert assistant.deliver_due_once(now+timedelta(hours=3))==0


def test_api_budget_clear_history_and_privacy(http,db):
    user=register(http,"assistant-api@example.com")
    charger=make_charger(db);db.commit()
    body=plan().model_dump(mode="json")
    preview=http.post("/api/v1/charging-estimates/preview",headers=csrf(http),json={**body,"available_minutes":30})
    assert preview.status_code==200 and preview.json()["time_budget"]["estimated_end_percent"]==50
    assert http.post("/api/v1/charging-estimates/preview",headers=csrf(http),json={**body,"available_minutes":0}).status_code==422
    start=http.post("/api/v1/sessions",headers=csrf(http),json={"charger_id":str(charger.id),"idempotency_key":"assistant-api-start","charge_estimate":body})
    sid=start.json()["session"]["id"];path=f"/api/v1/sessions/{sid}/assistant-reminder"
    result=http.put(path,headers=csrf(http),json={"enabled":True,"lead_minutes":10,"expected_version":0});assert result.status_code==200
    assert http.delete(f"/api/v1/sessions/{sid}/charge-estimate?version=1",headers=csrf(http)).status_code==204
    assert http.get(path).json()["enabled"] is False
    http.post(f"/api/v1/sessions/{sid}/unplug",headers=csrf(http),json={"idempotency_key":"assistant-api-end"})
    summary=http.get("/api/v1/sessions/history").json()["items"][0]
    assert summary["charge_summary"]["target_percent"]==80 and summary["charge_summary"]["is_estimate"]
    assert "return_reminder_sent_at" in summary
    assert http.post("/api/v1/research/assistant-preview",headers=csrf(http),json={"station_key":"PALO ALTO CA / HAMILTON #2","port_type":"Level 1","arrival_date":"2020-06-15","arrival_time":"22:00","plan":body}).status_code==403


def test_historical_model_suggestion_is_real_read_only_and_separate(http,db):
    result=register(http,"historical-assistant@example.com")
    user=db.get(User,UUID(result["id"]));user.role="researcher";db.commit()
    body={"station_key":"PALO ALTO CA / HAMILTON #2","port_type":"Level 1","arrival_date":"2020-06-15","arrival_time":"22:00","plan":plan().model_dump(mode="json"),"lead_minutes":10}
    positive=http.post("/api/v1/research/assistant-preview",headers=csrf(http),json=body)
    assert positive.status_code==200,positive.text
    assert positive.json()["suggest_return_reminder"] is True
    assert positive.json()["estimate"]["duration_seconds"]==7200
    negative=http.post("/api/v1/research/assistant-preview",headers=csrf(http),json={**body,"arrival_time":"08:00"})
    assert negative.status_code==200 and negative.json()["suggest_return_reminder"] is False
    changed=http.post("/api/v1/research/assistant-preview",headers=csrf(http),json={**body,"plan":{**body["plan"],"battery_capacity_kwh":90}}).json()
    assert changed["warning"]==positive.json()["warning"] and changed["estimate"]["duration_seconds"]==10800
    assert db.scalar(select(func.count()).select_from(ChargingSession))==0
    assert db.scalar(select(func.count()).select_from(AssistantReminder))==0
    assert db.scalar(select(func.count()).select_from(ChargeEstimate))==0
