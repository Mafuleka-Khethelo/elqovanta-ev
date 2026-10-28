"""Read-only arrival previews, independent of examiner-selected examples."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.clock import utcnow
from app.core.errors import fail
from app.ml.driver_advisory import current_advisory
from app.ml.runtime import get_runtime


def planned_arrival_instant(value: datetime, station_timezone: str, now: datetime) -> datetime:
    """Resolve a station wall time without silently guessing across DST changes."""
    if value.tzinfo is not None:
        fail(422, "arrival_timezone", "Enter the arrival date and time in the station's time zone, without an offset.")
    zone = ZoneInfo(station_timezone)
    candidates = set()
    for fold in (0, 1):
        instant = value.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
        if instant.astimezone(zone).replace(tzinfo=None) == value:
            candidates.add(instant)
    if not candidates:
        fail(422, "arrival_nonexistent", "That local time is skipped when the station's clocks change. Choose another time.")
    if len(candidates) > 1:
        fail(422, "arrival_ambiguous", "That local time occurs twice when the station's clocks change. Choose a time outside the repeated hour.")
    instant = candidates.pop()
    if instant <= now or instant > now + timedelta(days=7):
        fail(422, "arrival_range", "Choose a future arrival within the next 7 days, or select Now.")
    return instant


def driver_guidance(db, user, charger, *, now=None, port_type=None, arrival=None, planned_arrival=None):
    del db, user
    moment = now or utcnow()
    if planned_arrival is not None:
        arrival = planned_arrival_instant(planned_arrival, charger.timezone_name, moment)
    if not get_runtime().ready:
        return {"available": False, "reason": "unavailable"}
    return current_advisory(charger, port_type, arrival or moment, moment, planned=planned_arrival is not None)
