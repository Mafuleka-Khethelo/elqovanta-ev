"""Store the chosen observed port; never invent vehicle compatibility."""
from sqlalchemy import select
from app.core.errors import fail
from app.db.models import ChargerPortType


def selected_port(db, charger_id, value):
    ports = list(db.scalars(select(ChargerPortType.name).where(ChargerPortType.charger_id == charger_id).order_by(ChargerPortType.name)))
    if value is not None:
        if value not in ports:
            fail(422, "invalid_port", "Choose a port type listed for this charger.")
        return value
    return ports[0] if len(ports) == 1 else None
