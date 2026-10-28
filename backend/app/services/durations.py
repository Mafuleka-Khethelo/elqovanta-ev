"""Session durations are calculated on the server from timestamps.

Connected time runs from the reported plug-in until unplug, or until now while
the session is still open. Charging time is the sum of the reported charging
intervals. Noncharging occupancy is the difference. It includes pauses and time
after the driver reports that charging has finished. It is not a measurement of
how long a battery stayed full.
"""

from datetime import datetime, timedelta


class DurationError(ValueError):
    """Raised when stored timestamps cannot form a valid session."""


def summarise_seconds(
    plugged_in_at: datetime,
    unplugged_at: datetime | None,
    intervals: list[tuple[datetime, datetime | None]],
    now: datetime,
) -> tuple[int, int, int]:
    end = unplugged_at or now
    if end < plugged_in_at:
        raise DurationError("Connected duration cannot be negative.")
    connected = end - plugged_in_at
    charging = timedelta(0)
    previous_end: datetime | None = None
    for started_at, ended_at in sorted(intervals, key=lambda item: item[0]):
        interval_end = ended_at if ended_at is not None else now
        if unplugged_at is not None and ended_at is None:
            raise DurationError("A closed session still has an open charging interval.")
        if interval_end < started_at:
            raise DurationError("A charging interval cannot end before it starts.")
        if previous_end is not None and started_at < previous_end:
            raise DurationError("Charging intervals overlap.")
        charging += interval_end - started_at
        previous_end = interval_end
    if charging > connected:
        raise DurationError("Charging time cannot be longer than connected time.")
    noncharging = connected - charging
    return _whole_seconds(connected), _whole_seconds(charging), _whole_seconds(noncharging)


def _whole_seconds(value: timedelta) -> int:
    seconds = int(value.total_seconds())
    if seconds < 0:
        raise DurationError("Duration cannot be negative.")
    return seconds
