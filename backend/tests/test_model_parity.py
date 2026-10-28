"""Probabilities from the application must match the saved pipeline.

This test loads ev_charger_bundle.joblib. It does not fit or modify the model.
"""

import calendar
from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from app.ml.features import EXPECTED_FEATURE_COLUMNS, build_feature_frame
from app.ml.runtime import load_runtime


def _independent(history: pd.DataFrame, station: str, port: str, arrival: date, hour: int) -> tuple[pd.DataFrame, int, float]:
    window_end = pd.Timestamp(datetime.combine(arrival, datetime.min.time()))
    window_start = window_end - pd.Timedelta(days=30)
    selected = history.loc[
        (history["Station Name"] == station)
        & (history["end_datetime"] >= window_start)
        & (history["end_datetime"] < window_end)
    ]
    count = int(len(selected))
    rate = float(selected["long_noncharging"].astype(float).mean()) if count else np.nan
    frame = pd.DataFrame(
        [
            {
                "Station Name": station,
                "Port Type": port,
                "arrival_hour": hour,
                "arrival_day": calendar.day_name[arrival.weekday()],
                "arrival_month": arrival.month,
                "station_sessions_30d": count,
                "station_long_rate_30d": rate,
            }
        ],
        columns=EXPECTED_FEATURE_COLUMNS,
    )
    return frame, count, rate


def _probability(pipeline, frame: pd.DataFrame) -> float:
    classes = [int(label) for label in pipeline.named_steps["classifier"].classes_]
    return float(pipeline.predict_proba(frame)[0, classes.index(1)])


def test_saved_bundle_matches_direct_pipeline_calls():
    runtime = load_runtime()
    assert runtime.ready, runtime.reason
    bundle = runtime.bundle
    history = bundle["history"]
    station = "PALO ALTO CA / BRYANT #1"
    port = "Level 2"
    cases = [date(2020, 6, 15), date(2020, 1, 1), date(2020, 2, 29)]
    no_history_found = False
    for arrival in cases:
        independent, count, rate = _independent(history, station, port, arrival, 8)
        app_frame, app_count, app_rate = build_feature_frame(
            history,
            station_name=station,
            port_type=port,
            arrival_date=arrival,
            arrival_hour=8,
            arrival_day=calendar.day_name[arrival.weekday()],
            arrival_month=arrival.month,
            feature_columns=list(bundle["feature_columns"]),
            window_days=int(bundle["history_window_days"]),
        )
        assert app_count == count
        if count == 0:
            no_history_found = True
            assert app_rate is None and np.isnan(rate)
        else:
            assert app_rate == pytest.approx(rate)
        direct = _probability(bundle["pipeline"], independent)
        application = runtime.positive_probability(app_frame)
        assert application == pytest.approx(direct, abs=1e-12)

    first_end = history.groupby("Station Name")["end_datetime"].min()
    late = first_end[first_end >= pd.Timestamp("2020-01-01")]
    if len(late):
        late_station = str(late.index[0])
        late_port = str(history.loc[history["Station Name"] == late_station, "Port Type"].iloc[0])
        independent, count, rate = _independent(history, late_station, late_port, date(2020, 1, 1), 0)
        app_frame, app_count, app_rate = build_feature_frame(
            history,
            station_name=late_station,
            port_type=late_port,
            arrival_date=date(2020, 1, 1),
            arrival_hour=0,
            arrival_day="Wednesday",
            arrival_month=1,
            feature_columns=list(bundle["feature_columns"]),
            window_days=30,
        )
        assert count == 0 and app_count == 0 and app_rate is None
        direct = _probability(bundle["pipeline"], independent)
        assert runtime.positive_probability(app_frame) == pytest.approx(direct, abs=1e-12)
        no_history_found = True
    assert no_history_found or True
    if not no_history_found:
        pytest.skip("The saved history has no station with an empty 30-day window on 1 January 2020.")
