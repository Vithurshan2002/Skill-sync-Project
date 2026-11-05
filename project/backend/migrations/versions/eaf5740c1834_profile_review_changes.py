"""Preserve the original profile values throughout an administrator review."""

from alembic import op
import sqlalchemy as sa

revision = "eaf5740c1834"
down_revision = "d9e463fb0723"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("workers", sa.Column("review_baseline", sa.JSON(), nullable=True))


def downgrade():
    raise RuntimeError("Review evidence must not be discarded; restore a verified backup instead.")
