"""Store explicit booking end times; preserve historical appointments."""

import sqlalchemy as sa
from alembic import op

revision = "ac17962e3056"
down_revision = "fb06851d2945"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "bookings", sa.Column("scheduled_end_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        "booking_time_window",
        "bookings",
        "scheduled_end_at IS NULL OR (scheduled_end_at > scheduled_at "
        "AND (deadline_at IS NULL OR scheduled_end_at <= deadline_at))",
    )


def downgrade():
    raise RuntimeError(
        "Appointment times must not be discarded; restore a verified backup instead."
    )
