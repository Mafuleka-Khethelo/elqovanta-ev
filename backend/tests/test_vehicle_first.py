"""Account-owned selection and pre-start/queue plans, against PostgreSQL."""
from datetime import timedelta

from sqlalchemy import func, select

from app.core.clock import utcnow
from app.db.models import ChargeEstimate, ChargingSession, QueueEntry, User
from app.services import accounts
from app.services.sessions import direct_start, driver_action
from tests.conftest import csrf, register
from tests.test_charging_estimates import plan
from tests.test_coordination import make_charger, make_user


def test_selection_is_owned_persistent_and_safe_on_delete(http, db):
    me = register(http, "vehicle-selection@example.com")
    first = http.post("/api/v1/me/vehicles", headers=csrf(http), json={"nickname":"Everyday", "model_name":"Example", "battery_capacity_kwh":60}).json()
    second = http.post("/api/v1/me/vehicles", headers=csrf(http), json={"nickname":"Weekend", "battery_capacity_kwh":90}).json()
    endpoint = "/api/v1/me/vehicle-selection"
    assert http.get(endpoint).json()["selected_vehicle_id"] is None
    response = http.put(endpoint, headers=csrf(http), json={"vehicle_id":first["id"],"make_default":True})
    assert response.status_code == 200
    assert http.put(endpoint, headers=csrf(http), json={"vehicle_id":second["id"]}).json() == {
        "selected_vehicle_id": second["id"], "default_vehicle_id": first["id"]}
    other = make_user(db,"other-vehicle@example.com")
    foreign = accounts.add_vehicle(db,other,"Other car",None,None)
    db.commit()
    assert http.put(endpoint, headers=csrf(http), json={"vehicle_id":str(foreign.id)}).status_code == 404
    assert http.get(endpoint).json()["selected_vehicle_id"] == second["id"]
    assert http.delete(f'/api/v1/me/vehicles/{second["id"]}',headers=csrf(http)).status_code == 204
    assert http.get(endpoint).json() == {"selected_vehicle_id":first["id"],"default_vehicle_id":first["id"]}
    assert http.delete(f'/api/v1/me/vehicles/{first["id"]}',headers=csrf(http)).status_code == 204
    assert http.get(endpoint).json() == {"selected_vehicle_id":None,"default_vehicle_id":None}
    # Persisted independently of browser storage; changing cars creates no session.
    assert db.scalar(select(func.count()).select_from(ChargingSession)) == 0


def test_queue_plan_is_private_and_accept_attaches_fresh_reading_atomically(http, db):
    me = register(http,"vehicle-queue@example.com")
    from uuid import UUID
    user = db.get(User,UUID(me["id"]))
    vehicle = accounts.add_vehicle(db,user,"Everyday","Example car",None,battery_capacity_kwh=60,max_ac_kw=12)
    charger = make_charger(db)
    occupying = make_user(db,"occupying@example.com")
    now = utcnow()
    old = direct_start(db,occupying,charger.id,"old-session",now)
    db.commit()
    body = plan(vehicle_id=vehicle.id).model_dump(mode="json")
    join={"charger_id":str(charger.id),"idempotency_key":"join-with-vehicle-plan","charge_estimate":body}
    assert http.post("/api/v1/queue/join",headers=csrf(http),json=join).status_code == 200
    assert http.get("/api/v1/queue").json()["charge_plan"] == body
    assert db.scalar(select(func.count()).select_from(ChargeEstimate)) == 0
    summary=http.get(f"/api/v1/chargers/{charger.id}/charging-estimates").json()
    assert "charge_plan" not in summary and "vehicle_label" not in str(summary)
    driver_action(db,occupying,old.id,"unplug","free-bay",utcnow())
    db.commit()
    accept={"idempotency_key":"accept-vehicle-plan","charge_estimate":{**body,"current_percent":90,"target_percent":80}}
    assert http.post("/api/v1/queue/accept",headers=csrf(http),json=accept).status_code == 422
    assert http.get("/api/v1/queue").json()["participation"] == "offered"
    assert http.get("/api/v1/sessions/current").json()["session"] is None
    accept["charge_estimate"]["current_percent"] = 50
    response=http.post("/api/v1/queue/accept",headers=csrf(http),json=accept)
    assert response.status_code == 201, response.text
    again=http.post("/api/v1/queue/accept",headers=csrf(http),json=accept)
    assert again.json()["session"]["id"] == response.json()["session"]["id"]
    row=db.scalar(select(ChargeEstimate))
    assert row.current_percent == 50 and row.estimated_target_at-row.anchor_at == timedelta(minutes=90)
    session=db.get(ChargingSession,row.session_id)
    assert row.anchor_at == session.plugged_in_at
    assert db.scalar(select(func.count()).select_from(ChargeEstimate)) == 1
    assert http.get(f"/api/v1/chargers/{charger.id}").json()["app_status"] == "occupied"


def test_invalid_queue_plan_rolls_back_join(http, db):
    register(http,"invalid-queue-plan@example.com")
    charger=make_charger(db);db.commit()
    response=http.post("/api/v1/queue/join",headers=csrf(http),json={"charger_id":str(charger.id),"idempotency_key":"bad-queue-plan", "charge_estimate":plan(target_percent=10).model_dump(mode="json")})
    assert response.status_code == 422
    assert db.scalar(select(func.count()).select_from(QueueEntry)) == 0
