"""Experimental current-arrival use of the unchanged historical classifier.

The research lab remains restricted to 2020. This separate driver adapter uses
the actual arrival instant, the original seven features and the original frozen
history protocol. For dates after that history, the 30-day count is zero and
the rate remains missing; app sessions are never substituted for model history.
Only a plain warning is returned to drivers, with its validation limit explicit.
"""
import calendar
from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.ml.features import build_feature_frame, is_warning
from app.ml.runtime import get_runtime


@lru_cache(maxsize=2048)
def _assess(artifact: str, station: str, port: str, day: date, hour: int) -> tuple[bool, int]:
    runtime = get_runtime()
    bundle = runtime.bundle
    frame, count, _ = build_feature_frame(
        bundle["history"], station_name=station, port_type=port,
        arrival_date=day, arrival_hour=hour, arrival_day=calendar.day_name[day.weekday()],
        arrival_month=day.month, feature_columns=list(bundle["feature_columns"]),
        window_days=int(bundle["history_window_days"]),
    )
    probability = runtime.positive_probability(frame)
    return is_warning(probability, float(bundle["warning_cutoff"])), count


def current_advisory(charger, port_type: str | None, arrival: datetime, checked_at: datetime, *, planned: bool = False) -> dict:
    runtime = get_runtime()
    if not runtime.ready or runtime.bundle is None:
        return {"available": False, "reason": "unavailable"}
    supported = sorted(port for station, port in runtime.supported_pairs if station == charger.station_key)
    if not supported:
        return {"available": False, "reason": "unsupported_charger"}
    if port_type is None:
        if len(supported) != 1:
            return {"available": False, "reason": "choose_port", "port_types": supported}
        port_type = supported[0]
    if port_type not in supported:
        return {"available": False, "reason": "unsupported_port", "port_types": supported}
    if arrival.tzinfo is None:
        raise ValueError("Driver arrival must be a timezone-aware instant")
    local = arrival.astimezone(ZoneInfo(runtime.bundle["timezone"]))
    station_timezone = getattr(charger, "timezone_name", None) or runtime.bundle["timezone"]
    station_local = arrival.astimezone(ZoneInfo(station_timezone))
    try:
        warning, count = _assess(runtime.artifact_sha256 or "", charger.station_key, port_type, local.date(), local.hour)
    except Exception:
        # A model failure must not disable charging/queues or reveal internals.
        return {"available": False, "reason": "unavailable"}
    explanation = (
        "This experimental advisory estimates whether a session may include more than 30 minutes plugged in without charging. "
        "The saved model was evaluated on 2020 sessions, not current conditions. "
        + ("No station sessions exist in its frozen history for the preceding 30-day window. " if count == 0 else "")
        + "It uses the arrival hour, so changing minutes within the same hour may leave the result unchanged. "
        + "It does not predict waiting time, detect charge completion or reserve a bay. You can continue either way."
    )
    return {
        "available": True, "mode": "experimental_planned" if planned else "experimental_current", "warning": warning,
        "port_type": port_type, "port_types": supported,
        "arrival_local": local.isoformat(timespec="minutes"), "checked_at": checked_at,
        "arrival_station": station_local.isoformat(timespec="minutes"), "station_timezone": station_timezone,
        "timezone": runtime.bundle["timezone"], "title": "Charging advisory",
        "suggestion": "Plan your return after charging." if warning else "No warning flagged for this arrival.",
        "explanation": explanation, "action_label": "Choose a return reminder",
        "action_href": "/app/session#return-reminder",
    }
