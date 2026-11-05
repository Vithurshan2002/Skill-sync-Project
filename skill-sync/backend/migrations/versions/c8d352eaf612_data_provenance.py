"""Conservatively separate demo/test records from prospectively enrolled real work."""

from alembic import op
import sqlalchemy as sa

revision = "c8d352eaf612"
down_revision = "b7c241d9e501"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("users", "bookings"):
        op.add_column(
            table, sa.Column("data_source", sa.String(10), nullable=False, server_default="test")
        )
        op.create_check_constraint(
            f"{table}_data_source", table, "data_source IN ('demo','test','real')"
        )
    # All historical bookings remain test. No historical promotion based on current account state.
    op.execute(
        "UPDATE users SET data_source='demo' WHERE email IN ('arul.plumber@example.com','dinesh.electric@example.com','nihal.carpenter@example.com','samantha.welder@example.com')"
    )


def downgrade():
    raise RuntimeError(
        "Provenance evidence must not be discarded; restore a verified backup instead."
    )
