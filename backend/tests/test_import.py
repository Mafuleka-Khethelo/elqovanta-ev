"""Catalogue import keeps manager-owned operational fields."""

from datetime import datetime

import pandas as pd

from app.db.models import Charger, ChargerPortType
from app.services.catalogue import import_history


def _frame():
    return pd.DataFrame(
        {
            "Station Name": ["Alpha #2", "Alpha #2", "Beta", "Beta"],
            "Port Type": ["Level 2", "Level 1", "Level 2", "Level 2"],
            "Latitude": [37.44, 37.44001, 37.44, 37.50],
            "Longitude": [-122.16, -122.16001, -122.14, -122.20],
        }
    )


def test_import_is_idempotent_and_preserves_operations(db):
    first = import_history(db, _frame())
    db.commit()
    assert first.created == 2
    alpha = db.query(Charger).filter(Charger.station_key == "Alpha #2").one() if False else db.scalar(
        __import__("sqlalchemy").select(Charger).where(Charger.station_key == "Alpha #2")
    )
    alpha.service_capacity = 1
    alpha.coordination_enabled = True
    alpha.app_status = "available"
    alpha.status_source = "Manager: Ada"
    alpha.display_name = "Alpha friendly"
    alpha.display_name_custom = True
    db.add(ChargerPortType(charger_id=alpha.id, name="Manager port", origin="manager"))
    db.commit()

    second = import_history(db, _frame())
    db.commit()
    assert second.created == 0
    db.refresh(alpha)
    assert alpha.service_capacity == 1
    assert alpha.coordination_enabled is True
    assert alpha.app_status == "available"
    assert alpha.status_source == "Manager: Ada"
    assert alpha.display_name == "Alpha friendly"
    names = {row[0] for row in db.execute(__import__("sqlalchemy").select(ChargerPortType.name).where(ChargerPortType.charger_id == alpha.id))}
    assert names == {"Level 1", "Level 2", "Manager port"}
    beta = db.scalar(__import__("sqlalchemy").select(Charger).where(Charger.station_key == "Beta"))
    assert beta.coordinate_flag == "inconsistent"
    assert beta.coordinates_on_map is False
    assert alpha.coordinates_on_map is True
    assert alpha.station_key == "Alpha #2"
