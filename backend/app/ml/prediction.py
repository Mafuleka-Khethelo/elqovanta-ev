"""Run an explicit historical scenario and compare its 24 arrival hours.

All probabilities come from the frozen pipeline. The history window is built
once for the selected date; only arrival_hour changes across the comparison.
"""

import calendar
from datetime import date, timedelta

import pandas as pd

from app.core.clock import utcnow
from app.core.errors import fail
from app.ml.features import build_feature_frame, is_warning
from app.ml.runtime import LIMITATIONS, get_runtime


def score_scenario(station_key: str, port_type: str, arrival_date: date, arrival_time: str) -> dict:
    runtime = get_runtime()
    if not runtime.ready or runtime.bundle is None:
        fail(503, "prediction_unavailable", runtime.reason or "Historical prediction is unavailable.")
    if not date(2020, 1, 1) <= arrival_date <= date(2020, 12, 31):
        fail(422, "date_out_of_range", "Choose an arrival date from 1 January 2020 to 31 December 2020.")
    if (station_key, port_type) not in runtime.supported_pairs:
        fail(422, "unsupported_combination", "Choose a charger and port type that appear together in the saved history.")

    bundle = runtime.bundle
    hour = int(arrival_time[:2])
    weekday = calendar.day_name[arrival_date.weekday()]
    window_days = int(bundle["history_window_days"])
    frame, count, rate = build_feature_frame(
        bundle["history"],
        station_name=station_key,
        port_type=port_type,
        arrival_date=arrival_date,
        arrival_hour=hour,
        arrival_day=weekday,
        arrival_month=arrival_date.month,
        feature_columns=list(bundle["feature_columns"]),
        window_days=window_days,
    )
    hourly_frame = pd.concat([frame] * 24, ignore_index=True)
    hourly_frame["arrival_hour"] = range(24)
    probabilities = runtime.positive_probabilities(hourly_frame)
    cutoff = float(bundle["warning_cutoff"])
    probability = probabilities[hour]
    return {
        "mode": "historical",
        "station_key": station_key,
        "port_type": port_type,
        "arrival_local": f"{arrival_date.isoformat()}T{arrival_time}:00",
        "timezone": bundle["timezone"],
        "model_name": bundle["model_name"],
        "artifact_sha256": runtime.artifact_sha256,
        "schema_version": bundle["schema_version"],
        "noncharging_threshold_minutes": bundle["noncharging_threshold_minutes"],
        "warning_cutoff": cutoff,
        "probability": probability,
        "warning": is_warning(probability, cutoff),
        "station_sessions_30d": count,
        "station_long_rate_30d": rate,
        "history_window_start": (arrival_date - timedelta(days=window_days)).isoformat(),
        "history_window_end_exclusive": arrival_date.isoformat(),
        "derived_features": {
            "arrival_hour": hour,
            "arrival_day": weekday,
            "arrival_month": arrival_date.month,
        },
        "hourly": [
            {"arrival_hour": index, "probability": value, "warning": is_warning(value, cutoff)}
            for index, value in enumerate(probabilities)
        ],
        "computed_at": utcnow().isoformat(),
        "limitations": LIMITATIONS,
    }
