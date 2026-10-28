"""Summaries of the frozen historical sessions.

Filters use the historical wall-clock start time. They do not use application
sessions, and they do not turn co-located charger names into physical sites.
"""

from datetime import date

import pandas as pd

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def summarise_history(
    history: pd.DataFrame,
    *,
    station_key: str | None,
    start_date: date | None,
    end_date: date | None,
) -> dict:
    frame = history
    if station_key:
        frame = frame.loc[frame["Station Name"] == station_key]
    if start_date is not None:
        frame = frame.loc[frame["start_datetime"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        frame = frame.loc[frame["start_datetime"] < pd.Timestamp(end_date) + pd.Timedelta(days=1)]

    total = int(len(frame))
    if total == 0:
        return {
            "session_count": 0,
            "long_noncharging_count": 0,
            "long_noncharging_percent": None,
            "median_connected_minutes": None,
            "median_charging_minutes": None,
            "median_noncharging_minutes": None,
            "arrivals_by_hour": [{"hour": hour, "count": 0} for hour in range(24)],
            "arrivals_by_weekday": [{"weekday": name, "count": 0} for name in WEEKDAYS],
            "chargers": [],
        }

    long_count = int(frame["long_noncharging"].astype(float).sum())
    hours = frame["start_datetime"].dt.hour.value_counts().to_dict()
    weekdays = frame["start_datetime"].dt.dayofweek.value_counts().to_dict()
    grouped = (
        frame.groupby("Station Name", sort=False)
        .agg(session_count=("long_noncharging", "size"), long_rate=("long_noncharging", "mean"))
        .reset_index()
    )
    grouped = grouped.sort_values(["session_count", "Station Name"], ascending=[False, True]).head(10)
    chargers = [
        {
            "station_key": str(row["Station Name"]),
            "session_count": int(row["session_count"]),
            "long_noncharging_percent": round(float(row["long_rate"]) * 100, 1),
        }
        for _, row in grouped.iterrows()
    ]
    return {
        "session_count": total,
        "long_noncharging_count": long_count,
        "long_noncharging_percent": round(long_count / total * 100, 1),
        "median_connected_minutes": _median(frame, "total_minutes"),
        "median_charging_minutes": _median(frame, "charging_minutes"),
        "median_noncharging_minutes": _median(frame, "noncharging_minutes"),
        "arrivals_by_hour": [{"hour": hour, "count": int(hours.get(hour, 0))} for hour in range(24)],
        "arrivals_by_weekday": [
            {"weekday": WEEKDAYS[index], "count": int(weekdays.get(index, 0))} for index in range(7)
        ],
        "chargers": chargers,
    }


def _median(frame: pd.DataFrame, column: str) -> float | None:
    if column not in frame.columns or frame.empty:
        return None
    value = frame[column].median()
    if pd.isna(value):
        return None
    return round(float(value), 1)
