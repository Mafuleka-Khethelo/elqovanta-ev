"""Rules that do not need PostgreSQL or the saved model file."""

from datetime import datetime, timedelta, timezone

import calendar

import numpy as np
import pandas as pd
import pytest

from app.ml.features import build_feature_frame, is_long_noncharging, is_warning
from app.services.durations import DurationError, summarise_seconds


def test_warning_cutoff_is_strict():
    assert is_warning(0.17, 0.17) is False
    assert is_warning(0.1700000001, 0.17) is True
    assert is_warning(0.1699, 0.17) is False


def test_exactly_thirty_noncharging_minutes_is_not_positive():
    assert is_long_noncharging(100, 70, 30) is False
    assert is_long_noncharging(40, 10, 30) is False
    assert is_long_noncharging(40, 9, 30) is True


def _history():
    rows = [
        ("Alpha", "Level 2", datetime(2019, 12, 2, 8, 0), True),
        ("Alpha", "DC Fast", datetime(2019, 12, 2, 9, 0), False),
        ("Alpha", "Level 2", datetime(2019, 12, 1, 23, 59), True),
        ("Alpha", "Level 2", datetime(2020, 1, 1, 0, 0), True),
        ("Alpha", "Level 2", datetime(2020, 1, 30, 12, 0), False),
        ("Alpha", "Level 2", datetime(2020, 2, 28, 23, 0), True),
        ("Alpha", "Level 2", datetime(2020, 2, 29, 1, 0), False),
        ("Alpha", "Level 2", datetime(2020, 3, 1, 0, 0), True),
        ("Beta", "Level 2", datetime(2020, 1, 15, 0, 0), True),
    ]
    return pd.DataFrame(
        {
            "Station Name": [row[0] for row in rows],
            "Port Type": [row[1] for row in rows],
            "end_datetime": [row[2] for row in rows],
            "long_noncharging": [row[3] for row in rows],
        }
    )


def _features(history, station, port, day, hour=8):
    arrival = datetime.fromisoformat(day).date()
    return build_feature_frame(
        history,
        station_name=station,
        port_type=port,
        arrival_date=arrival,
        arrival_hour=hour,
        arrival_day=calendar.day_name[arrival.weekday()],
        arrival_month=arrival.month,
        feature_columns=[
            "Station Name",
            "Port Type",
            "arrival_hour",
            "arrival_day",
            "arrival_month",
            "station_sessions_30d",
            "station_long_rate_30d",
        ],
        window_days=30,
    )


def test_history_window_boundaries_and_exclusions():
    history = _history()
    frame, count, rate = _features(history, "Alpha", "Level 2", "2020-01-01")
    # 2019-12-02 is included. 2019-12-01 is before the window. 2020-01-01 is the arrival day.
    assert count == 2
    assert rate == pytest.approx(0.5)
    assert frame.loc[0, "Port Type"] == "Level 2"
    assert int(frame.loc[0, "station_sessions_30d"]) == 2

    _frame, leap_count, leap_rate = _features(history, "Alpha", "DC Fast", "2020-02-29")
    # Window starts 2020-01-30. Arrival day and 1 March are excluded. Another port on Alpha still counts.
    assert leap_count == 2
    assert leap_rate == pytest.approx(0.5)

    _frame, other_count, other_rate = _features(history, "Beta", "Level 2", "2020-02-10")
    assert other_count == 1
    assert other_rate == pytest.approx(1.0)

    _frame, empty_count, empty_rate = _features(history, "Gamma", "Level 2", "2020-06-01")
    assert empty_count == 0
    assert empty_rate is None
    assert not np.isnan(frame.loc[0, "station_long_rate_30d"])
    assert np.isnan(_frame.loc[0, "station_long_rate_30d"])


def test_multiple_pauses_have_exact_durations():
    start = datetime(2020, 6, 1, 10, 0, tzinfo=timezone.utc)
    intervals = [
        (start, start + timedelta(minutes=10)),
        (start + timedelta(minutes=25), start + timedelta(minutes=40)),
    ]
    connected, charging, noncharging = summarise_seconds(start, start + timedelta(minutes=50), intervals, start)
    assert (connected, charging, noncharging) == (50 * 60, 25 * 60, 25 * 60)


def test_open_session_includes_the_running_interval():
    start = datetime(2020, 6, 1, 10, 0, tzinfo=timezone.utc)
    now = start + timedelta(minutes=12)
    connected, charging, noncharging = summarise_seconds(start, None, [(start, None)], now)
    assert (connected, charging, noncharging) == (12 * 60, 12 * 60, 0)


def test_overlapping_intervals_are_rejected():
    start = datetime(2020, 6, 1, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(DurationError):
        summarise_seconds(
            start,
            start + timedelta(minutes=30),
            [(start, start + timedelta(minutes=20)), (start + timedelta(minutes=10), start + timedelta(minutes=25))],
            start,
        )
