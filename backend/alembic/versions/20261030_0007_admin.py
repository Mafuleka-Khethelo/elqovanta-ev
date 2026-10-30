"""Read-only project administrator access for the existing sole manager."""
from alembic import op
import sqlalchemy as sa

revision = "20261030_0007"
down_revision = "20261030_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    # This project's existing owner is its single manager. Preserve that login
    # and all password hashes. Ambiguous multi-manager installations grant none;
    # their operator must explicitly choose with `app.cli set-admin`.
    op.execute("UPDATE users SET is_admin = true WHERE role = 'manager' AND (SELECT count(*) FROM users WHERE role = 'manager') = 1")


def downgrade():
    op.drop_column("users", "is_admin")
