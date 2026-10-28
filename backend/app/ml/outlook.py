"""An explicit historical scenario for the charger detail page.

The default is labelled 15 June 2020, not today's clock silently placed in
2020. Changing the date or port runs the saved pipeline on the new inputs.
"""

from datetime import date

from app.core.errors import fail
from app.ml.prediction import score_scenario
from app.ml.runtime import get_runtime


def score_outlook(
    station_key: str,
    port_types: list[str],
    *,
    arrival_date: date = date(2020, 6, 15),
    port_type: str | None = None,
    arrival_hour: int = 8,
) -> dict:
    runtime = get_runtime()
    if not runtime.ready or runtime.bundle is None:
        return {"available": False, "reason": runtime.reason or "The model is not loaded."}
    supported = sorted({name for name in port_types if (station_key, name) in runtime.supported_pairs})
    if not supported:
        return {"available": False, "reason": "This charger has no supported port in the saved Palo Alto history."}
    port = port_type if port_type is not None else supported[0]
    if port not in supported:
        fail(422, "unsupported_combination", "Choose one of this charger's historical port types.")
    result = score_scenario(station_key, port, arrival_date, f"{arrival_hour:02d}:00")
    return {"available": True, "reason": None, "supported_port_types": supported, **result}
