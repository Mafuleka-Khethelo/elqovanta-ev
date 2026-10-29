"""Car-specific charging calculations; preserve sessions and original model."""
from alembic import op
import sqlalchemy as sa

revision = "20261029_0004"
down_revision = "20261028_0003"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("battery_capacity_kwh", "max_ac_kw", "max_dc_kw"):
        op.add_column("vehicles", sa.Column(name, sa.Double(), nullable=True))
    op.create_table("charge_estimates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("charging_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vehicle_label", sa.String(140), nullable=False),
        *[sa.Column(n, sa.Double(), nullable=False) for n in ("battery_capacity_kwh", "current_percent", "target_percent")],
        sa.Column("charging_kind", sa.String(2), nullable=False),
        sa.Column("average_power_kw", sa.Double(), nullable=False),
        sa.Column("effective_power_kw", sa.Double(), nullable=False),
        sa.Column("anchor_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estimated_target_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("near_notified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("target_notified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.UniqueConstraint("session_id", "idempotency_key", name="uq_estimate_request"),
        sa.UniqueConstraint("session_id", "version", name="uq_estimate_version"),
        sa.CheckConstraint("battery_capacity_kwh > 0 AND battery_capacity_kwh <= 500", name="ck_estimate_capacity"),
        sa.CheckConstraint("current_percent >= 0 AND current_percent <= target_percent AND target_percent <= 100", name="ck_estimate_percent"),
        sa.CheckConstraint("effective_power_kw > 0 AND effective_power_kw <= 1000", name="ck_estimate_power"),
    )
    op.create_index("ix_charge_estimates_session_id", "charge_estimates", ["session_id"])
    op.create_index("ix_charge_estimates_estimated_target_at", "charge_estimates", ["estimated_target_at"])
    op.create_index("uq_active_charge_estimate", "charge_estimates", ["session_id"], unique=True, postgresql_where=sa.text("is_active"))


def downgrade():
    op.drop_table("charge_estimates")
    for name in ("max_dc_kw", "max_ac_kw", "battery_capacity_kwh"):
        op.drop_column("vehicles", name)
