"""Operational tables.

These records belong to the website. They are separate from the historical
research table stored inside the saved model bundle. Application sessions must
not be appended to that frozen history.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('driver', 'manager', 'researcher')", name="ck_user_role"),
        UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(32), default="driver")
    is_demonstration: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    __table_args__ = (Index("ix_login_attempts_email_created", "email", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255))
    succeeded: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    nickname: Mapped[str] = mapped_column(String(40))
    model_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    port_preference: Mapped[str | None] = mapped_column(String(60), nullable=True)
    battery_capacity_kwh: Mapped[float | None] = mapped_column(Double, nullable=True)
    max_ac_kw: Mapped[float | None] = mapped_column(Double, nullable=True)
    max_dc_kw: Mapped[float | None] = mapped_column(Double, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="vehicles")


class Charger(Base):
    __tablename__ = "chargers"
    __table_args__ = (
        CheckConstraint(
            "app_status IN ('unknown', 'available', 'occupied', 'offline', 'paused')",
            name="ck_charger_app_status",
        ),
        CheckConstraint(
            "service_capacity IS NULL OR service_capacity >= 1",
            name="ck_charger_capacity",
        ),
        CheckConstraint(
            "coordinate_flag IN ('ok', 'missing', 'invalid', 'inconsistent')",
            name="ck_charger_coordinate_flag",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    station_key: Mapped[str] = mapped_column(String(500), unique=True)
    display_name: Mapped[str] = mapped_column(String(500))
    display_name_custom: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    is_historical: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    latitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    coordinates_on_map: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    coordinate_flag: Mapped[str] = mapped_column(String(32), default="missing")
    app_status: Mapped[str] = mapped_column(String(32), default="unknown")
    status_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status_source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    timezone_name: Mapped[str] = mapped_column(String(64), default="UTC", server_default="UTC")
    status_version: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    service_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coordination_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    port_types: Mapped[list["ChargerPortType"]] = relationship(
        back_populates="charger", cascade="all, delete-orphan"
    )


class ChargerPortType(Base):
    __tablename__ = "charger_port_types"
    __table_args__ = (
        UniqueConstraint("charger_id", "name", name="uq_charger_port_name"),
        CheckConstraint("origin IN ('historical', 'manager')", name="ck_port_origin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    charger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chargers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    origin: Mapped[str] = mapped_column(String(32))

    charger: Mapped[Charger] = relationship(back_populates="port_types")


class ManagerAssignment(Base):
    __tablename__ = "manager_assignments"
    __table_args__ = (UniqueConstraint("manager_id", "charger_id", name="uq_manager_charger"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    manager_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    charger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chargers.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Favourite(Base):
    __tablename__ = "favourites"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    charger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chargers.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChargingSession(Base):
    __tablename__ = "charging_sessions"
    __table_args__ = (
        CheckConstraint(
            "state IN ('charging', 'paused', 'finished_plugged', 'unplugged')",
            name="ck_session_state",
        ),
        UniqueConstraint("user_id", "idempotency_key", name="uq_session_idempotency"),
        Index(
            "uq_active_session_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("unplugged_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    charger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chargers.id", ondelete="CASCADE"), index=True)
    state: Mapped[str] = mapped_column(String(32))
    port_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    plugged_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    unplugged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(80))
    is_demonstration: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    intervals: Mapped[list["ChargingInterval"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    events: Mapped[list["SessionEvent"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ChargeEstimate(Base):
    """Versioned calculation snapshots, separate from the saved ML pipeline."""
    __tablename__ = "charge_estimates"
    __table_args__ = (
        UniqueConstraint("session_id", "idempotency_key", name="uq_estimate_request"),
        UniqueConstraint("session_id", "version", name="uq_estimate_version"),
        Index("uq_active_charge_estimate", "session_id", unique=True, postgresql_where=text("is_active")),
        CheckConstraint("battery_capacity_kwh > 0 AND battery_capacity_kwh <= 500", name="ck_estimate_capacity"),
        CheckConstraint("current_percent >= 0 AND current_percent <= target_percent AND target_percent <= 100", name="ck_estimate_percent"),
        CheckConstraint("effective_power_kw > 0 AND effective_power_kw <= 1000", name="ck_estimate_power"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("charging_sessions.id", ondelete="CASCADE"), index=True)
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    vehicle_label: Mapped[str] = mapped_column(String(140))
    battery_capacity_kwh: Mapped[float] = mapped_column(Double)
    current_percent: Mapped[float] = mapped_column(Double)
    target_percent: Mapped[float] = mapped_column(Double)
    charging_kind: Mapped[str] = mapped_column(String(2))
    average_power_kw: Mapped[float] = mapped_column(Double)
    effective_power_kw: Mapped[float] = mapped_column(Double)
    anchor_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estimated_target_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    version: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    near_notified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    target_notified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    idempotency_key: Mapped[str] = mapped_column(String(80))


class ChargingInterval(Base):
    __tablename__ = "charging_intervals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("charging_sessions.id", ondelete="CASCADE"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[ChargingSession] = relationship(back_populates="intervals")


class SessionEvent(Base):
    __tablename__ = "session_events"
    __table_args__ = (
        UniqueConstraint("session_id", "idempotency_key", name="uq_session_event_idempotency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("charging_sessions.id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    session: Mapped[ChargingSession] = relationship(back_populates="events")


class QueueEntry(Base):
    __tablename__ = "queue_entries"
    __table_args__ = (
        CheckConstraint(
            "state IN ('waiting', 'offered', 'accepted', 'left', 'expired', 'cancelled')",
            name="ck_queue_state",
        ),
        UniqueConstraint("user_id", "idempotency_key", name="uq_queue_idempotency"),
        Index(
            "uq_active_queue_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("state IN ('waiting', 'offered')"),
        ),
        Index("ix_queue_charger_state_joined", "charger_id", "state", "joined_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    charger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chargers.id", ondelete="CASCADE"), index=True)
    state: Mapped[str] = mapped_column(String(32))
    port_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    offer_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    offer_round: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("charging_sessions.id", ondelete="SET NULL"), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(80))
    accept_idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_demonstration: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("charger_id", "driver_id", name="uq_conversation_driver_charger"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    charger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chargers.id", ondelete="CASCADE"), index=True)
    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    client_request_id: Mapped[str] = mapped_column(String(80), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReadMarker(Base):
    __tablename__ = "read_markers"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_key: Mapped[str] = mapped_column(String(200), unique=True)
    title: Mapped[str] = mapped_column(String(140))
    body: Mapped[str] = mapped_column(String(500))
    destination: Mapped[str] = mapped_column(String(200))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PredictionLog(Base):
    """A historical lab request. This is not an application charging session."""

    __tablename__ = "prediction_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    station_key: Mapped[str] = mapped_column(String(500))
    port_type: Mapped[str] = mapped_column(String(120))
    arrival_local: Mapped[str] = mapped_column(String(32))
    timezone_name: Mapped[str] = mapped_column(String(64))
    artifact_sha256: Mapped[str] = mapped_column(String(64))
    model_name: Mapped[str] = mapped_column(String(80))
    probability: Mapped[float] = mapped_column(Double)
    warning: Mapped[bool] = mapped_column(Boolean)
    station_sessions_30d: Mapped[int] = mapped_column(Integer)
    station_long_rate_30d: Mapped[float | None] = mapped_column(Double, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())


class DepartureReport(Base):
    __tablename__ = "departure_reports"
    __table_args__ = (CheckConstraint("state IN ('active', 'retracted', 'expired', 'ended')", name="ck_departure_state"),)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("charging_sessions.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(20), default="active")


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        CheckConstraint("state IN ('pending', 'delivered', 'cancelled')", name="ck_reminder_state"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_reminder_request"),
        Index("ix_reminders_due", "state", "due_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("charging_sessions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(20), default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(80))
    notification_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("notifications.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChargerReport(Base):
    __tablename__ = "charger_reports"
    __table_args__ = (
        CheckConstraint("category IN ('not_working', 'access_blocked')", name="ck_report_category"),
        CheckConstraint("state IN ('open', 'acknowledged', 'resolved')", name="ck_report_state"),
        UniqueConstraint("reporter_id", "idempotency_key", name="uq_report_request"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    charger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chargers.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(30))
    details: Mapped[str] = mapped_column(String(1000))
    state: Mapped[str] = mapped_column(String(20), default="open")
    manager_response: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    responder_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class HistoricalDemonstration(Base):
    """Explicit examiner context for a labelled demonstration driver only."""
    __tablename__ = "historical_demonstrations"
    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    researcher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    charger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chargers.id", ondelete="CASCADE"))
    port_type: Mapped[str] = mapped_column(String(120))
    arrival_local: Mapped[str] = mapped_column(String(32))
    timezone_name: Mapped[str] = mapped_column(String(64))
    suggest_reminder: Mapped[bool] = mapped_column(Boolean)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
