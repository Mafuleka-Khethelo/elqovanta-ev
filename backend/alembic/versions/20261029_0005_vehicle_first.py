"""Private vehicle selection and a provisional waiting driver's charge plan."""
from alembic import op
import sqlalchemy as sa

revision = "20261029_0005"
down_revision = "20261029_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("vehicle_preferences",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("selected_vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("default_vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True))
    op.add_column("queue_entries", sa.Column("charge_plan", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("queue_entries", "charge_plan")
    op.drop_table("vehicle_preferences")
