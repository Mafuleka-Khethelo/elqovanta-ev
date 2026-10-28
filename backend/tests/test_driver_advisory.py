"""Real-model parity and ordinary-driver access for the new automatic adapter."""
import calendar
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.db.models import Charger, ChargerPortType, ChargingSession, HistoricalDemonstration, PredictionLog, QueueEntry, User
from app.ml.driver_advisory import _assess
from app.ml.guidance import driver_guidance, planned_arrival_instant
from app.ml.runtime import load_runtime
from app.services.queues import accept_offer, join_queue
from app.services.sessions import direct_start, driver_action
from tests.conftest import csrf, register
from tests.test_coordination import make_charger, make_user

STATION, PORT = "PALO ALTO CA / HAMILTON #2", "Level 1"


@pytest.fixture(scope="module")
def runtime():
    result = load_runtime()
    assert result.ready, result.reason
    _assess.cache_clear()
    return result


def test_current_date_matches_original_pipeline_without_backdating_or_substituting_history(runtime):
    now = datetime(2026, 10, 28, 20, 0, tzinfo=timezone.utc)
    local = now.astimezone(ZoneInfo(runtime.bundle["timezone"]))
    original_rows = len(runtime.bundle["history"])
    result = driver_guidance(None, SimpleNamespace(is_demonstration=False), SimpleNamespace(station_key=STATION), now=now, port_type=PORT)
    frame = pd.DataFrame([{"Station Name": STATION, "Port Type": PORT,
        "arrival_hour": local.hour, "arrival_day": calendar.day_name[local.weekday()], "arrival_month": local.month,
        "station_sessions_30d": 0, "station_long_rate_30d": np.nan}], columns=runtime.bundle["feature_columns"])
    classifier = runtime.bundle["pipeline"].named_steps["classifier"]
    probability = runtime.bundle["pipeline"].predict_proba(frame)[0, list(classifier.classes_).index(1)]
    assert result["available"] and result["mode"] == "experimental_current"
    assert result["warning"] == bool(probability > runtime.bundle["warning_cutoff"])
    assert result["arrival_local"].startswith("2026-10-28")
    assert "No station sessions" in result["explanation"]
    assert "not current conditions" in result["explanation"]
    assert len(runtime.bundle["history"]) == original_rows
    assert not {"probability", "warning_cutoff", "artifact_sha256", "station_sessions_30d", "derived_features"}.intersection(result)


def test_unchanged_inputs_are_cached_and_real_changed_arrivals_change_warning(runtime, monkeypatch):
    _assess.cache_clear()
    calls = []
    original = runtime.positive_probability
    def score(frame):
        calls.append(frame.copy())
        return original(frame)
    monkeypatch.setattr(runtime, "positive_probability", score)
    charger = SimpleNamespace(station_key=STATION)
    day = datetime(2020, 6, 15, 7, tzinfo=ZoneInfo("America/Los_Angeles"))
    first = driver_guidance(None, None, charger, now=day, port_type=PORT)
    repeat = driver_guidance(None, None, charger, now=day + timedelta(minutes=45), port_type=PORT)
    later = driver_guidance(None, None, charger, now=day.replace(hour=22), port_type=PORT)
    assert first["warning"] is False and repeat["warning"] is False and later["warning"] is True
    assert len(calls) == 2
    assert list(calls[0].columns) == runtime.bundle["feature_columns"]
    _assess.cache_clear()


def test_unsupported_and_failed_assessments_are_honest_and_do_not_leak_errors(runtime, monkeypatch):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert driver_guidance(None, None, SimpleNamespace(station_key="New manager station"), now=now) == {"available": False, "reason": "unsupported_charger"}
    unsupported = driver_guidance(None, None, SimpleNamespace(station_key=STATION), now=now, port_type="Invented plug")
    assert unsupported["available"] is False and unsupported["reason"] == "unsupported_port"
    _assess.cache_clear()
    def broken(frame):
        raise RuntimeError("private numerical package details")
    monkeypatch.setattr(runtime, "positive_probability", broken)
    unavailable = driver_guidance(None, None, SimpleNamespace(station_key=STATION), now=now, port_type=PORT)
    assert unavailable == {"available": False, "reason": "unavailable"}


def test_new_registered_driver_gets_advisory_without_examiner_or_demo_flag(http, db, runtime):
    account = register(http, "automatic-driver@example.com")
    assert account["is_demonstration"] is False
    charger = Charger(station_key=STATION, display_name="Hamilton", app_status="available", coordination_enabled=True, service_capacity=1)
    db.add(charger); db.flush()
    db.add(ChargerPortType(charger_id=charger.id, name=PORT, origin="historical")); db.commit()
    result = http.get(f"/api/v1/chargers/{charger.id}/guidance", params={"port_type": PORT, "arrival_date": "2020-01-01"})
    assert result.status_code == 200
    assert result.json()["available"] is True and result.json()["mode"] == "experimental_current"
    assert not result.json()["arrival_local"].startswith("2020-")
    assert db.scalar(select(func.count()).select_from(PredictionLog)) == 0
    response = http.post("/api/v1/sessions", headers=csrf(http), json={"charger_id": str(charger.id), "port_type": PORT, "idempotency_key": "ordinary-start-anyway"})
    assert response.status_code == 201
    session = response.json()["session"]
    assert session["port_type"] == PORT
    own = http.get(f"/api/v1/sessions/{session['id']}/guidance")
    assert own.status_code == 200 and own.json()["available"]
    arrival = datetime.fromisoformat(session["plugged_in_at"]).astimezone(ZoneInfo(runtime.bundle["timezone"]))
    assert own.json()["arrival_local"] == arrival.isoformat(timespec="minutes")
    http.cookies.clear()
    register(http, "other-automatic-driver@example.com")
    assert http.get(f"/api/v1/sessions/{session['id']}/guidance").status_code == 404


def test_chosen_port_survives_waiting_list_handover_and_unknown_port_is_rejected(db):
    first, second = make_user(db, "port-first@example.com"), make_user(db, "port-next@example.com")
    charger, now = make_charger(db), datetime.now(timezone.utc)
    for port in ("Level 1", "Level 2"):
        db.add(ChargerPortType(charger_id=charger.id, name=port, origin="manager"))
    db.flush()
    with pytest.raises(HTTPException) as exc:
        direct_start(db, first, charger.id, "unknown-port-key", now, "Invented plug")
    assert exc.value.status_code == 422
    session = direct_start(db, first, charger.id, "selected-port-start", now, "Level 2")
    assert session.port_type == "Level 2"
    entry = join_queue(db, second, charger.id, "selected-port-wait", now, "Level 1")
    db.commit()
    driver_action(db, first, session.id, "unplug", "selected-port-unplug", now + timedelta(seconds=1))
    next_session = accept_offer(db, second, "selected-port-accept", now + timedelta(seconds=2))
    assert next_session.port_type == entry.port_type == "Level 1"


def test_model_unavailability_does_not_block_manual_charging(db, monkeypatch):
    driver, charger = make_user(db, "no-model-driver@example.com"), make_charger(db)
    monkeypatch.setattr("app.ml.guidance.get_runtime", lambda: SimpleNamespace(ready=False))
    assert driver_guidance(db, driver, charger)["available"] is False
    session = direct_start(db, driver, charger.id, "manual-without-model", datetime.now(timezone.utc))
    assert session.state == "charging"


def test_planned_arrival_uses_station_time_and_original_pipeline(runtime, monkeypatch):
    now = datetime(2026, 10, 29, 10, tzinfo=timezone.utc)
    selected = datetime(2026, 10, 30, 1, 15)
    charger = SimpleNamespace(station_key=STATION, timezone_name="Africa/Johannesburg")
    calls = []
    original = runtime.positive_probability
    def score(frame):
        calls.append(frame.copy())
        return original(frame)
    monkeypatch.setattr(runtime, "positive_probability", score)
    _assess.cache_clear()
    result = driver_guidance(None, None, charger, now=now, port_type=PORT, planned_arrival=selected)
    assert result["mode"] == "experimental_planned"
    assert result["arrival_station"] == "2026-10-30T01:15+02:00"
    assert result["arrival_local"] == "2026-10-29T16:15-07:00"
    assert result["station_timezone"] == charger.timezone_name
    frame = calls[0]
    assert frame.iloc[0]["arrival_hour"] == 16 and frame.iloc[0]["arrival_day"] == "Thursday"
    assert frame.iloc[0]["arrival_month"] == 10 and frame.iloc[0]["station_sessions_30d"] == 0
    assert pd.isna(frame.iloc[0]["station_long_rate_30d"])
    assert result["warning"] == bool(original(frame) > runtime.bundle["warning_cutoff"])
    assert len(runtime.bundle["history"]) == 259366
    _assess.cache_clear()


@pytest.mark.parametrize("value,code", [
    (datetime(2026, 10, 29, 2), "arrival_range"),
    (datetime(2026, 11, 6, 2), "arrival_range"),
    (datetime(2026, 10, 30, 2, tzinfo=timezone.utc), "arrival_timezone"),
    (datetime(2026, 11, 1, 1, 30), "arrival_ambiguous"),
])
def test_invalid_planned_arrivals_are_rejected(value, code):
    with pytest.raises(HTTPException) as exc:
        planned_arrival_instant(value, "America/Los_Angeles", datetime(2026, 10, 29, 10, tzinfo=timezone.utc))
    assert exc.value.status_code == 422 and exc.value.detail["code"] == code


def test_skipped_dst_time_and_seven_day_boundary():
    with pytest.raises(HTTPException) as exc:
        planned_arrival_instant(datetime(2026, 3, 8, 2, 30), "America/Los_Angeles", datetime(2026, 3, 7, tzinfo=timezone.utc))
    assert exc.value.detail["code"] == "arrival_nonexistent"
    now = datetime(2026, 10, 29, 10, tzinfo=timezone.utc)
    assert planned_arrival_instant(datetime(2026, 11, 5, 12), "Africa/Johannesburg", now) == now + timedelta(days=7)
    with pytest.raises(HTTPException):
        planned_arrival_instant(datetime(2026, 10, 29, 12), "Africa/Johannesburg", now)


def test_planning_api_is_read_only_and_does_not_override_real_session(http, db, runtime, monkeypatch):
    register(http, "planned-driver@example.com")
    charger = Charger(station_key=STATION, display_name="Hamilton", timezone_name="America/Los_Angeles", app_status="available", coordination_enabled=True, service_capacity=1)
    db.add(charger); db.flush()
    db.add(ChargerPortType(charger_id=charger.id, name=PORT, origin="historical")); db.commit()
    now = datetime(2026, 10, 29, 10, tzinfo=timezone.utc)
    monkeypatch.setattr("app.api.v1.chargers.utcnow", lambda: now)
    params = {"port_type": PORT, "planned_arrival": "2026-10-30T15:45"}
    response = http.get(f"/api/v1/chargers/{charger.id}/guidance", params=params)
    assert response.status_code == 200 and response.json()["mode"] == "experimental_planned"
    assert response.json()["arrival_station"] == "2026-10-30T15:45-07:00"
    for model in (ChargingSession, QueueEntry, HistoricalDemonstration, PredictionLog):
        assert db.scalar(select(func.count()).select_from(model)) == 0
    for value in ("2020-06-15T07:00", "2026-10-30T15:45+02:00", "not-a-time"):
        assert http.get(f"/api/v1/chargers/{charger.id}/guidance", params={**params, "planned_arrival": value}).status_code == 422
    assert http.get(f"/api/v1/chargers/{charger.id}/guidance", params={"port_type": PORT}).json()["mode"] == "experimental_current"
    started = http.post("/api/v1/sessions", headers=csrf(http), json={"charger_id": str(charger.id), "port_type": PORT, "idempotency_key": "start-after-planning"})
    assert started.status_code == 201
    session = started.json()["session"]
    own = http.get(f"/api/v1/sessions/{session['id']}/guidance", params=params).json()
    assert own["mode"] == "experimental_current"
    actual = datetime.fromisoformat(session["plugged_in_at"]).astimezone(ZoneInfo(charger.timezone_name))
    assert own["arrival_station"] == actual.isoformat(timespec="minutes")
