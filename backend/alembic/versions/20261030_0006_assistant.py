"""Optional pre-target reminders and manager-reported per-port power."""
from alembic import op
import sqlalchemy as sa

revision = "20261030_0006"
down_revision = "20261029_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("charger_port_types", sa.Column("power_kw", sa.Double(), nullable=True))
    op.add_column("charger_port_types", sa.Column("charging_kind", sa.String(2), nullable=True))
    op.add_column("charger_port_types", sa.Column("power_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint("ck_port_power", "charger_port_types", "(power_kw IS NULL AND charging_kind IS NULL) OR (power_kw IS NOT NULL AND charging_kind IS NOT NULL AND power_kw > 0 AND power_kw <= 1000 AND charging_kind IN ('AC','DC'))")
    op.create_table("assistant_reminders",
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("charging_sessions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("lead_minutes", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimate_version", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("lead_minutes >= 1 AND lead_minutes <= 120", name="ck_assistant_lead"))
    op.create_index("ix_assistant_reminders_user_id", "assistant_reminders", ["user_id"])
    op.create_index("ix_assistant_reminders_due_at", "assistant_reminders", ["due_at"])


def downgrade():
    op.drop_table("assistant_reminders")
    op.drop_constraint("ck_port_power", "charger_port_types", type_="check")
    for name in ("power_updated_at", "charging_kind", "power_kw"):
        op.drop_column("charger_port_types", name)
