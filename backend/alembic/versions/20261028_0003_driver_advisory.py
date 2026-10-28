"""Remember the driver's selected port without changing model artifacts/history."""
from alembic import op
import sqlalchemy as sa

revision = "20261028_0003"
down_revision = "20261028_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("charging_sessions", sa.Column("port_type", sa.String(120), nullable=True))
    op.add_column("queue_entries", sa.Column("port_type", sa.String(120), nullable=True))


def downgrade():
    op.drop_column("queue_entries", "port_type")
    op.drop_column("charging_sessions", "port_type")
