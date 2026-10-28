"""Historical feature construction for the frozen pipeline.

The server builds all seven model inputs. Callers cannot submit their own
30-day counts or rates. History is filtered by the exact station name and by
when the earlier session finished, not by when it started. The whole selected
arrival day is excluded, including an evening arrival. That matches the daily
history protocol used when the model was trained.

Datetime values in the bundle are timezone-naive Palo Alto wall-clock times.
This module does not convert them and does not apply a PST/PDT correction.
"""

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

EXPECTED_FEATURE_COLUMNS = [
    "Station Name",
    "Port Type",
    "arrival_hour",
    "arrival_day",
    "arrival_month",
    "station_sessions_30d",
    "station_long_rate_30d",
]

EXPECTED_HISTORY_COLUMNS = [
    "Station Name",
    "Port Type",
    "Latitude",
    "Longitude",
    "start_datetime",
    "end_datetime",
    "total_minutes",
    "charging_minutes",
    "noncharging_minutes",
    "long_noncharging",
]


def is_long_noncharging(total_minutes: float, charging_minutes: float, threshold_minutes: float = 30) -> bool:
    """The research label. Exactly 30 noncharging minutes is class 0."""
    return (total_minutes - charging_minutes) > threshold_minutes


def is_warning(probability: float, cutoff: float) -> bool:
    """The warning rule is strict. A probability equal to the cutoff is not a warning."""
    return float(probability) > float(cutoff)


def build_feature_frame(
    history: pd.DataFrame,
    *,
    station_name: str,
    port_type: str,
    arrival_date: date,
    arrival_hour: int,
    arrival_day: str,
    arrival_month: int,
    feature_columns: list[str],
    window_days: int,
) -> tuple[pd.DataFrame, int, float | None]:
    """Return a one-row frame, the session count, and the long-session rate.

    The rate is None when the window is empty. The frame itself keeps NaN so the
    fitted pipeline can apply its own missing-value treatment. Do not replace
    that NaN with zero.
    """
    window_start = datetime.combine(arrival_date, time.min) - timedelta(days=window_days)
    window_end = datetime.combine(arrival_date, time.min)
    start_ts = pd.Timestamp(window_start)
    end_ts = pd.Timestamp(window_end)
    names = history["Station Name"]
    ended = history["end_datetime"]
    selected = history.loc[(names == station_name) & (ended >= start_ts) & (ended < end_ts)]
    count = int(len(selected))
    if count == 0:
        rate_value = np.nan
        public_rate = None
    else:
        rate_value = float(selected["long_noncharging"].astype(float).mean())
        public_rate = rate_value
    row = {
        "Station Name": station_name,
        "Port Type": port_type,
        "arrival_hour": int(arrival_hour),
        "arrival_day": arrival_day,
        "arrival_month": int(arrival_month),
        "station_sessions_30d": count,
        "station_long_rate_30d": rate_value,
    }
    frame = pd.DataFrame([row], columns=list(feature_columns))
    return frame, count, public_rate
