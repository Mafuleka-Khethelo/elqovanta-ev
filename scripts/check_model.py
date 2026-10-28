r"""Check the real model without starting PostgreSQL or the website.

From the project root:
    backend\.venv\Scripts\python scripts\check_model.py

Prints inspectable JSON. Never trains, saves or changes the model or history.
"""

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.prediction import score_scenario
from app.ml.runtime import load_runtime


def main() -> None:
    runtime = load_runtime()
    if not runtime.ready:
        raise SystemExit(runtime.reason)
    original_sha = hashlib.sha256((ROOT / "ev_charger_bundle.joblib").read_bytes()).hexdigest()
    assert original_sha == runtime.artifact_sha256, "Loaded model differs from the project-root artifact."
    bundle = runtime.bundle
    pipeline = bundle["pipeline"]
    positive = list(pipeline.named_steps["classifier"].classes_).index(1)
    checks = []
    for station in ["PALO ALTO CA / HAMILTON #2", "PALO ALTO CA / BRYANT #1"]:
        for arrival in [date(2020, 6, 15), date(2020, 1, 1), date(2020, 10, 22)]:
            result = score_scenario(station, "Level 1", arrival, "08:00")
            # Construct independent inputs directly from the frozen history.
            history = bundle["history"]
            end = pd.Timestamp(arrival)
            window = history.loc[
                history["Station Name"].eq(station)
                & history["end_datetime"].ge(end - pd.Timedelta(days=30))
                & history["end_datetime"].lt(end)
            ]
            frame = pd.DataFrame([
                {
                    "Station Name": station,
                    "Port Type": "Level 1",
                    "arrival_hour": hour,
                    "arrival_day": end.day_name(),
                    "arrival_month": arrival.month,
                    "station_sessions_30d": len(window),
                    "station_long_rate_30d": float(window["long_noncharging"].mean()) if len(window) else np.nan,
                }
                for hour in range(24)
            ], columns=bundle["feature_columns"])
            direct = pipeline.predict_proba(frame)[:, positive]
            repeated = pipeline.predict_proba(frame)[:, positive]
            displayed = [item["probability"] for item in result["hourly"]]
            assert np.allclose(displayed, direct, atol=1e-12, rtol=0)
            assert np.allclose(repeated, direct, atol=1e-12, rtol=0)
            assert float(np.ptp(direct)) > 1e-6, "This example did not respond to arrival-hour changes."
            checks.append({
                "station": station,
                "port": "Level 1",
                "arrival_date": str(arrival),
                "earlier_sessions": len(window),
                "earlier_long_rate": result["station_long_rate_30d"],
                "minimum": {"hour": int(direct.argmin()), "percent": round(float(direct.min()) * 100, 4)},
                "maximum": {"hour": int(direct.argmax()), "percent": round(float(direct.max()) * 100, 4)},
                "max_error_against_pipeline": float(np.max(np.abs(direct - displayed))),
                "max_repeat_difference": float(np.max(np.abs(direct - repeated))),
                "parity_passed": True,
                "repeatability_passed": True,
            })
    print(json.dumps({
        "model": bundle["model_name"],
        "artifact_sha256": original_sha,
        "loaded_matches_original": True,
        "stored_metrics_match_reference": runtime.metrics_match_reference,
        "history_rows": len(bundle["history"]),
        "compared_predictions": len(checks) * 24,
        "numerical_tolerance": 1e-12,
        "checks": checks,
    }, indent=2))


if __name__ == "__main__":
    main()
