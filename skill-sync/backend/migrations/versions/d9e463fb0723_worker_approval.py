"""Store private worker review feedback; preserve existing approval decisions."""

from alembic import op
import sqlalchemy as sa

revision = "d9e463fb0723"
down_revision = "c8d352eaf612"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("workers", sa.Column("review_note", sa.String(500), nullable=True))
    # Seeded badges are not approval decisions. Preserve only recorded admin approvals.
    op.execute("""
        UPDATE workers SET verified = false
        WHERE verified = true AND NOT EXISTS (
            SELECT 1 FROM audit_events a JOIN users u ON u.id = a.actor_id
            WHERE a.record_id = workers.id AND a.action = 'worker.verification'
              AND a.details->>'after' = 'true' AND u.role = 'admin'
        )
    """)


def downgrade():
    raise RuntimeError("Review evidence must not be discarded; restore a verified backup instead.")
