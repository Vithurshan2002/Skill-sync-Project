"""Track deadlines, confirmed outcomes, cancellation attribution and complaints."""

from alembic import op
import sqlalchemy as sa

revision = "b7c241d9e501"
down_revision = "a2ba729fb94c"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("deadline_at", "reported_completed_at", "confirmed_at"):
        op.add_column("bookings", sa.Column(name, sa.DateTime(timezone=True), nullable=True))
    op.add_column("bookings", sa.Column("cancelled_by_role", sa.String(20), nullable=True))
    op.add_column("bookings", sa.Column("prediction", sa.JSON(), nullable=True))
    op.alter_column("bookings", "status", type_=sa.String(30))
    op.alter_column("booking_events", "status", type_=sa.String(30))
    op.drop_constraint("booking_status", "bookings", type_="check")
    op.create_check_constraint(
        "booking_status",
        "bookings",
        "status IN ('pending','accepted','in_progress','awaiting_confirmation','completed','rejected','cancelled')",
    )
    op.create_check_constraint(
        "booking_deadline", "bookings", "deadline_at IS NULL OR deadline_at > scheduled_at"
    )
    op.drop_index("uq_active_booking_request", table_name="bookings")
    op.create_index(
        "uq_active_booking_request",
        "bookings",
        ["request_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('pending','accepted','in_progress','awaiting_confirmation')"
        ),
    )
    op.create_table(
        "complaints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "booking_id", sa.String(36), sa.ForeignKey("bookings.id"), nullable=False, unique=True
        ),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("resolution", sa.String(2000)),
        sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending','upheld','dismissed')", name="complaint_status"),
    )


def downgrade():
    # A downgrade would discard outcome evidence and cannot represent pending confirmations.
    raise RuntimeError("Restore a verified test-database backup to revert this outcome migration.")
