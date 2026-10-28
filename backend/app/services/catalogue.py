"""Import historical charger names from the frozen research table.

Identity is the exact Station Name. A suffix such as "#2" is part of that key.
Distinct names are not counted as verified physical sites, and distinct port
types are not counted as physical connectors.

Coordinate rule, applied per exact station name:
- A point is valid when both numbers are finite, latitude is -90 to 90,
  longitude is -180 to 180, and the point is not 0,0.
- If no valid point exists, the charger stays in the list and is left off the map.
- If the valid points span more than 0.01 degrees of latitude or longitude,
  they are flagged inconsistent and left off the map. No single pin is invented.
- Otherwise the median latitude and longitude is the representative map point.

Running the import again does not duplicate chargers or port types, and it does
not change manager-owned operational fields: display name once customised,
app-reported status, status source, capacity, or coordination setting.
"""

from dataclasses import dataclass

import math
import statistics

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.db.models import Charger, ChargerPortType

COORDINATE_SPAN_LIMIT = 0.01


@dataclass
class ImportReport:
    created: int = 0
    refreshed: int = 0
    port_types_added: int = 0
    inconsistent_coordinates: int = 0
    omitted_from_map: int = 0


def classify_coordinates(latitudes, longitudes) -> tuple[str, float | None, float | None]:
    points: list[tuple[float, float]] = []
    saw_invalid = False
    for latitude, longitude in zip(latitudes, longitudes):
        if pd.isna(latitude) or pd.isna(longitude):
            continue
        lat = float(latitude)
        lon = float(longitude)
        valid = (
            math.isfinite(lat)
            and math.isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
            and not (abs(lat) < 1e-8 and abs(lon) < 1e-8)
        )
        if not valid:
            saw_invalid = True
            continue
        points.append((lat, lon))
    if not points:
        return ("invalid" if saw_invalid else "missing"), None, None
    lat_span = max(point[0] for point in points) - min(point[0] for point in points)
    lon_span = max(point[1] for point in points) - min(point[1] for point in points)
    if lat_span > COORDINATE_SPAN_LIMIT or lon_span > COORDINATE_SPAN_LIMIT:
        return "inconsistent", None, None
    return "ok", statistics.median(point[0] for point in points), statistics.median(point[1] for point in points)


def import_history(db: Session, history: pd.DataFrame) -> ImportReport:
    required = {"Station Name", "Port Type", "Latitude", "Longitude"}
    missing = required.difference(history.columns)
    if missing:
        raise ValueError("Historical table is missing columns: " + ", ".join(sorted(missing)))

    report = ImportReport()
    now = utcnow()
    grouped = history.dropna(subset=["Station Name"]).groupby("Station Name", sort=True)
    for station_name, group in grouped:
        station_key = str(station_name)
        flag, latitude, longitude = classify_coordinates(group["Latitude"], group["Longitude"])
        on_map = flag == "ok"
        if flag == "inconsistent":
            report.inconsistent_coordinates += 1
        if not on_map:
            report.omitted_from_map += 1

        charger = db.scalar(select(Charger).where(Charger.station_key == station_key))
        if charger is None:
            charger = Charger(
                station_key=station_key,
                display_name=station_key,
                display_name_custom=False,
                is_historical=True,
                timezone_name="America/Los_Angeles",
                latitude=latitude,
                longitude=longitude,
                coordinates_on_map=on_map,
                coordinate_flag=flag,
                app_status="unknown",
                status_updated_at=now,
                status_source="Catalogue import",
                status_version=0,
                service_capacity=None,
                coordination_enabled=False,
                created_at=now,
                updated_at=now,
            )
            db.add(charger)
            db.flush()
            report.created += 1
        else:
            charger.is_historical = True
            charger.latitude = latitude
            charger.longitude = longitude
            charger.coordinates_on_map = on_map
            charger.coordinate_flag = flag
            charger.updated_at = now
            report.refreshed += 1

        known = set(db.scalars(select(ChargerPortType.name).where(ChargerPortType.charger_id == charger.id)))
        for port_name in sorted({str(value) for value in group["Port Type"].dropna().unique()}):
            if not port_name or port_name in known:
                continue
            db.add(ChargerPortType(charger_id=charger.id, name=port_name, origin="historical"))
            known.add(port_name)
            report.port_types_added += 1
    db.flush()
    return report
