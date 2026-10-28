"""Initial ChargeConnect tables.

Revision ID: 20261019_0001
Revises:
Create Date: 2026-10-19

Operational records only. The historical research table stays inside the saved
model bundle and is not created here.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261019_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("is_demonstration", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('driver', 'manager')", name="ck_user_role"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])

    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_login_attempts_created_at", "login_attempts", ["created_at"])
    op.create_index("ix_login_attempts_email_created", "login_attempts", ["email", "created_at"])

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nickname", sa.String(40), nullable=False),
        sa.Column("model_name", sa.String(60), nullable=True),
        sa.Column("port_preference", sa.String(60), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vehicles_user_id", "vehicles", ["user_id"])

    op.create_table(
        "chargers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("station_key", sa.String(500), nullable=False),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("display_name_custom", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_historical", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("latitude", sa.Double(), nullable=True),
        sa.Column("longitude", sa.Double(), nullable=True),
        sa.Column("coordinates_on_map", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("coordinate_flag", sa.String(32), nullable=False),
        sa.Column("app_status", sa.String(32), nullable=False),
        sa.Column("status_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status_source", sa.String(200), nullable=True),
        sa.Column("status_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("service_capacity", sa.Integer(), nullable=True),
        sa.Column("coordination_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "app_status IN ('unknown', 'available', 'occupied', 'offline', 'paused')",
            name="ck_charger_app_status",
        ),
        sa.CheckConstraint("service_capacity IS NULL OR service_capacity >= 1", name="ck_charger_capacity"),
        sa.CheckConstraint(
            "coordinate_flag IN ('ok', 'missing', 'invalid', 'inconsistent')",
            name="ck_charger_coordinate_flag",
        ),
        sa.UniqueConstraint("station_key", name="uq_chargers_station_key"),
    )

    op.create_table(
        "charger_port_types",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("charger_id", sa.Uuid(), sa.ForeignKey("chargers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("origin", sa.String(32), nullable=False),
        sa.CheckConstraint("origin IN ('historical', 'manager')", name="ck_port_origin"),
        sa.UniqueConstraint("charger_id", "name", name="uq_charger_port_name"),
    )
    op.create_index("ix_charger_port_types_charger_id", "charger_port_types", ["charger_id"])

    op.create_table(
        "manager_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("manager_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("charger_id", sa.Uuid(), sa.ForeignKey("chargers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("manager_id", "charger_id", name="uq_manager_charger"),
    )
    op.create_index("ix_manager_assignments_manager_id", "manager_assignments", ["manager_id"])
    op.create_index("ix_manager_assignments_charger_id", "manager_assignments", ["charger_id"])

    op.create_table(
        "favourites",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("charger_id", sa.Uuid(), sa.ForeignKey("chargers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "charging_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("charger_id", sa.Uuid(), sa.ForeignKey("chargers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("plugged_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unplugged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("is_demonstration", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('charging', 'paused', 'finished_plugged', 'unplugged')",
            name="ck_session_state",
        ),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_session_idempotency"),
    )
    op.create_index("ix_charging_sessions_user_id", "charging_sessions", ["user_id"])
    op.create_index("ix_charging_sessions_charger_id", "charging_sessions", ["charger_id"])
    op.create_index(
        "uq_active_session_per_user",
        "charging_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("unplugged_at IS NULL"),
    )

    op.create_table(
        "charging_intervals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("charging_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_charging_intervals_session_id", "charging_intervals", ["session_id"])

    op.create_table(
        "session_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("charging_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("idempotency_key", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "idempotency_key", name="uq_session_event_idempotency"),
    )
    op.create_index("ix_session_events_session_id", "session_events", ["session_id"])
    op.create_index("ix_session_events_created_at", "session_events", ["created_at"])

    op.create_table(
        "queue_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("charger_id", sa.Uuid(), sa.ForeignKey("chargers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("offer_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("offer_round", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("charging_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("accept_idempotency_key", sa.String(80), nullable=True),
        sa.Column("is_demonstration", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('waiting', 'offered', 'accepted', 'left', 'expired', 'cancelled')",
            name="ck_queue_state",
        ),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_queue_idempotency"),
    )
    op.create_index("ix_queue_entries_user_id", "queue_entries", ["user_id"])
    op.create_index("ix_queue_entries_charger_id", "queue_entries", ["charger_id"])
    op.create_index("ix_queue_charger_state_joined", "queue_entries", ["charger_id", "state", "joined_at"])
    op.create_index(
        "uq_active_queue_per_user",
        "queue_entries",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('waiting', 'offered')"),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("charger_id", sa.Uuid(), sa.ForeignKey("chargers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("driver_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("charger_id", "driver_id", name="uq_conversation_driver_charger"),
    )
    op.create_index("ix_conversations_charger_id", "conversations", ["charger_id"])
    op.create_index("ix_conversations_driver_id", "conversations", ["driver_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("client_request_id", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("client_request_id", name="uq_messages_client_request_id"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"])
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])

    op.create_table(
        "read_markers",
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_key", sa.String(200), nullable=False),
        sa.Column("title", sa.String(140), nullable=False),
        sa.Column("body", sa.String(500), nullable=False),
        sa.Column("destination", sa.String(200), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_key", name="uq_notifications_event_key"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])

    op.create_table(
        "prediction_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("station_key", sa.String(500), nullable=False),
        sa.Column("port_type", sa.String(120), nullable=False),
        sa.Column("arrival_local", sa.String(32), nullable=False),
        sa.Column("timezone_name", sa.String(64), nullable=False),
        sa.Column("artifact_sha256", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(80), nullable=False),
        sa.Column("probability", sa.Double(), nullable=False),
        sa.Column("warning", sa.Boolean(), nullable=False),
        sa.Column("station_sessions_30d", sa.Integer(), nullable=False),
        sa.Column("station_long_rate_30d", sa.Double(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_prediction_logs_user_id", "prediction_logs", ["user_id"])


def downgrade() -> None:
    for name in (
        "prediction_logs",
        "notifications",
        "read_markers",
        "messages",
        "conversations",
        "queue_entries",
        "session_events",
        "charging_intervals",
        "charging_sessions",
        "favourites",
        "manager_assignments",
        "charger_port_types",
        "chargers",
        "vehicles",
        "login_attempts",
        "auth_sessions",
        "users",
    ):
        op.drop_table(name)
