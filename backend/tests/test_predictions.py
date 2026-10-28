"""Verify interactive results against the real saved model, not fake scores."""

import calendar
from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.db.models import Charger, ChargerPortType, PredictionLog, User
from app.ml.guidance import driver_guidance
from app.ml.outlook import score_outlook
from app.ml.prediction import score_scenario
from app.ml.runtime import load_runtime
from tests.conftest import csrf, register

STATION = "PALO ALTO CA / HAMILTON #2"
PORT = "Level 1"


@pytest.fixture(scope="module")
def real_model():
    runtime = load_runtime()
    assert runtime.ready, runtime.reason
    return runtime


@pytest.mark.parametrize("arrival", [date(2020, 6, 15), date(2020, 1, 1), date(2020, 10, 22)])
def test_all_displayed_hours_match_independent_pipeline_inputs(real_model, arrival):
    result = score_scenario(STATION, PORT, arrival, "08:30")
    bundle = real_model.bundle
    history = bundle["history"]
    end = pd.Timestamp(arrival)
    earlier = history.loc[
        history["Station Name"].eq(STATION)
        & history["end_datetime"].ge(end - pd.Timedelta(days=30))
        & history["end_datetime"].lt(end)
    ]
    rate = float(earlier["long_noncharging"].mean()) if len(earlier) else np.nan
    independent = pd.DataFrame([
        {
            "Station Name": STATION,
            "Port Type": PORT,
            "arrival_hour": hour,
            "arrival_day": calendar.day_name[arrival.weekday()],
            "arrival_month": arrival.month,
            "station_sessions_30d": len(earlier),
            "station_long_rate_30d": rate,
        }
        for hour in range(24)
    ], columns=bundle["feature_columns"])
    pipeline = bundle["pipeline"]
    positive = list(pipeline.named_steps["classifier"].classes_).index(1)
    direct = pipeline.predict_proba(independent)[:, positive]
    assert [item["arrival_hour"] for item in result["hourly"]] == list(range(24))
    assert [item["probability"] for item in result["hourly"]] == pytest.approx(direct, abs=1e-12)
    assert [item["warning"] for item in result["hourly"]] == [bool(value > 0.17) for value in direct]
    assert result["probability"] == pytest.approx(direct[8], abs=1e-12)
    assert result["station_sessions_30d"] == len(earlier)
    assert result["station_long_rate_30d"] == pytest.approx(rate)
    assert result["history_window_end_exclusive"] == str(arrival)
    assert result["artifact_sha256"] == real_model.artifact_sha256


def test_changed_inputs_respond_and_repeated_inputs_reproduce(real_model):
    morning = score_scenario(STATION, PORT, date(2020, 6, 15), "07:00")
    evening = score_scenario(STATION, PORT, date(2020, 6, 15), "22:00")
    repeat = score_scenario(STATION, PORT, date(2020, 6, 15), "07:59")
    other_date = score_scenario(STATION, PORT, date(2020, 1, 1), "07:00")
    assert morning["probability"] != pytest.approx(evening["probability"], abs=1e-6)
    assert morning["warning"] is False and evening["warning"] is True
    assert morning["probability"] == pytest.approx(repeat["probability"], abs=1e-12)
    assert morning["probability"] != pytest.approx(other_date["probability"], abs=1e-6)
    assert morning["station_sessions_30d"] != other_date["station_sessions_30d"]


def test_empty_history_is_missing_instead_of_zero(real_model):
    result = score_scenario("PALO ALTO CA / BRYANT #1", PORT, date(2020, 10, 22), "08:00")
    assert result["station_sessions_30d"] == 0
    assert result["station_long_rate_30d"] is None
    assert len(result["hourly"]) == 24
    assert 0 <= result["probability"] <= 1


def test_outlook_uses_explicit_inputs_and_rejects_unsupported_ports(real_model):
    result = score_outlook(STATION, [PORT, "Manager-only connector"], arrival_date=date(2020, 1, 1), port_type=PORT, arrival_hour=22)
    assert result["available"] is True
    assert result["arrival_local"] == "2020-01-01T22:00:00"
    assert result["supported_port_types"] == [PORT]
    with pytest.raises(HTTPException) as exc:
        score_outlook(STATION, [PORT, "Manager-only connector"], port_type="Manager-only connector")
    assert exc.value.status_code == 422
    assert score_outlook("A newly created charger", [PORT])["available"] is False


@pytest.mark.parametrize("arrival", [date(2019, 12, 31), date(2021, 1, 1)])
def test_scenarios_outside_evaluation_year_are_rejected(real_model, arrival):
    with pytest.raises(HTTPException) as exc:
        score_scenario(STATION, PORT, arrival, "08:00")
    assert exc.value.status_code == 422


def test_researcher_can_run_lab_and_charger_comparison(http, db, real_model):
    account = register(http, "model-demo@example.com")
    user = db.get(User, UUID(account["id"]))
    user.role = "researcher"
    charger = Charger(station_key=STATION, display_name="Hamilton", coordinate_flag="missing")
    db.add(charger)
    db.flush()
    db.add(ChargerPortType(charger_id=charger.id, name=PORT, origin="historical"))
    db.commit()
    response = http.post("/api/v1/research/predict", headers=csrf(http), json={
        "station_key": STATION, "port_type": PORT, "arrival_date": "2020-06-15", "arrival_time": "22:00",
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result["hourly"]) == 24
    assert result["warning"] is True
    assert db.scalar(select(func.count()).select_from(PredictionLog)) == 1
    outlook = http.get(f"/api/v1/chargers/{charger.id}/outlook", params={
        "arrival_date": "2020-06-15", "port_type": PORT, "arrival_hour": 22,
    })
    assert outlook.status_code == 200, outlook.text
    assert outlook.json()["probability"] == pytest.approx(result["probability"], abs=1e-12)
    assert http.get(f"/api/v1/chargers/{charger.id}/outlook", params={"arrival_hour": 24}).status_code == 422
    assert http.get(f"/api/v1/chargers/{charger.id}/outlook", params={"arrival_date": "2026-10-22"}).status_code == 422
    http.cookies.clear()
    assert http.get(f"/api/v1/chargers/{charger.id}/outlook").status_code == 401


def test_legacy_research_context_does_not_gate_automatic_driver_advisory(http, db, real_model):
    from app.core.clock import utcnow
    from app.db.models import HistoricalDemonstration
    from tests.test_coordination import make_user

    account = register(http, "examiner-demo@example.com")
    researcher = db.get(User, UUID(account["id"]))
    researcher.role = "researcher"
    driver = make_user(db, "labelled-demo@example.com")
    driver.is_demonstration = True
    charger = Charger(station_key=STATION, display_name="Hamilton", is_historical=True, coordinate_flag="missing", timezone_name="America/Los_Angeles")
    db.add(charger)
    db.commit()
    request = {"driver_id": str(driver.id), "station_key": STATION, "port_type": PORT, "arrival_date": "2020-06-15", "arrival_time": "22:00"}
    response = http.post("/api/v1/research/demonstrations", headers=csrf(http), json=request)
    assert response.status_code == 200, response.text
    row = db.get(HistoricalDemonstration, driver.id)
    assert row.suggest_reminder is True
    result = driver_guidance(db, driver, charger, port_type=PORT)
    assert result["available"] is True
    assert result["mode"] == "experimental_current"
    assert "historical_arrival_local" not in result
    assert not {"probability", "warning_cutoff", "artifact_sha256", "derived_features"}.intersection(result)
    before = db.scalar(select(func.count()).select_from(PredictionLog))
    assert http.post("/api/v1/research/demonstrations", headers=csrf(http), json=request).status_code == 200
    assert db.scalar(select(func.count()).select_from(PredictionLog)) == before
    assert driver_guidance(db, driver, charger, now=row.expires_at, port_type=PORT)["available"] is True
    driver.is_demonstration = False
    assert driver_guidance(db, driver, charger, port_type=PORT)["available"] is True
    driver.is_demonstration = True
    assert http.delete(f"/api/v1/research/demonstrations/{driver.id}", headers=csrf(http)).status_code == 204
    db.expire_all()
    assert driver_guidance(db, driver, charger, port_type=PORT)["available"] is True

def test_driver_guidance_does_not_expose_runtime_errors(monkeypatch):
    monkeypatch.setattr("app.ml.guidance.get_runtime", lambda: SimpleNamespace(ready=False, bundle=None, reason="private version details"))
    result = driver_guidance(None, SimpleNamespace(is_demonstration=True), None)
    assert result["available"] is False
    assert "private" not in str(result)


def test_driver_cannot_read_research_or_request_raw_predictions(http, db, real_model):
    register(http, "driver-view@example.com")
    charger = Charger(station_key=STATION, display_name="Hamilton", coordinate_flag="missing")
    db.add(charger)
    db.flush()
    db.add(ChargerPortType(charger_id=charger.id, name=PORT, origin="historical"))
    db.commit()
    for path in ["/research/model", "/research/options", "/research/insights", f"/chargers/{charger.id}/outlook"]:
        assert http.get(f"/api/v1{path}").status_code == 403, path
    response = http.post("/api/v1/research/predict", headers=csrf(http), json={
        "station_key": STATION, "port_type": PORT, "arrival_date": "2020-06-15", "arrival_time": "22:00",
    })
    assert response.status_code == 403
    guidance = http.get(f"/api/v1/chargers/{charger.id}/guidance", params={"port_type": PORT})
    assert guidance.status_code == 200
    assert guidance.json()["available"] is True
    assert guidance.json()["mode"] == "experimental_current"
    assert "probability" not in guidance.json()
    http.cookies.clear()
    assert http.get(f"/api/v1/chargers/{charger.id}/guidance").status_code == 401
    assert http.get("/api/v1/research/model").status_code == 401
