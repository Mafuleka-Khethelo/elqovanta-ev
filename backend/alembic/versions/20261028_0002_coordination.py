"""Examiner separation and persistent driver coordination features.

Revision ID: 20261028_0002
Revises: 20261019_0001
"""
from alembic import op
import sqlalchemy as sa

revision = "20261028_0002"
down_revision = "20261019_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_user_role", "users", type_="check")
    op.create_check_constraint("ck_user_role", "users", "role IN ('driver', 'manager', 'researcher')")
    op.add_column("chargers", sa.Column("timezone_name", sa.String(64), nullable=False, server_default="UTC"))
    op.execute("UPDATE chargers SET timezone_name = 'America/Los_Angeles' WHERE is_historical = true")
    op.create_table("departure_reports",
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("charging_sessions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.CheckConstraint("state IN ('active', 'retracted', 'expired', 'ended')", name="ck_departure_state"))
    op.create_index("ix_departure_reports_user_id", "departure_reports", ["user_id"])
    op.create_table("reminders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("charging_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("notification_id", sa.Uuid(), sa.ForeignKey("notifications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("state IN ('pending', 'delivered', 'cancelled')", name="ck_reminder_state"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_reminder_request"))
    op.create_index("ix_reminders_due", "reminders", ["state", "due_at"])
    for column in ("session_id", "user_id"):
        op.create_index(f"ix_reminders_{column}", "reminders", [column])
    op.create_table("charger_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reporter_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("charger_id", sa.Uuid(), sa.ForeignKey("chargers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("details", sa.String(1000), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("manager_response", sa.String(1000), nullable=True),
        sa.Column("responder_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("category IN ('not_working', 'access_blocked')", name="ck_report_category"),
        sa.CheckConstraint("state IN ('open', 'acknowledged', 'resolved')", name="ck_report_state"),
        sa.UniqueConstraint("reporter_id", "idempotency_key", name="uq_report_request"))
    for column in ("reporter_id", "charger_id"):
        op.create_index(f"ix_charger_reports_{column}", "charger_reports", [column])
    op.create_table("historical_demonstrations",
        sa.Column("driver_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("researcher_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("charger_id", sa.Uuid(), sa.ForeignKey("chargers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("port_type", sa.String(120), nullable=False),
        sa.Column("arrival_local", sa.String(32), nullable=False),
        sa.Column("timezone_name", sa.String(64), nullable=False),
        sa.Column("suggest_reminder", sa.Boolean(), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    for table in ("historical_demonstrations", "charger_reports", "reminders", "departure_reports"):
        op.drop_table(table)
    op.drop_column("chargers", "timezone_name")
    # Never silently demote an examiner account during a rollback.
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM users WHERE role = 'researcher') THEN RAISE EXCEPTION 'Remove or reassign researcher accounts before downgrade'; END IF; END $$")
    op.drop_constraint("ck_user_role", "users", type_="check")
    op.create_check_constraint("ck_user_role", "users", "role IN ('driver', 'manager')")
