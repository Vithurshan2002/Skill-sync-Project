"""Optional private locations for distance matching; retain all existing records."""

import sqlalchemy as sa
from alembic import op

revision = "fb06851d2945"
down_revision = "eaf5740c1834"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("workers", "service_requests"):
        op.add_column(table, sa.Column("latitude", sa.Float(), nullable=True))
        op.add_column(table, sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("workers", sa.Column("service_radius_km", sa.Float(), nullable=True))
    op.create_check_constraint(
        "worker_location",
        "workers",
        "(latitude IS NULL AND longitude IS NULL AND service_radius_km IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL AND service_radius_km IS NOT NULL AND latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180 AND service_radius_km BETWEEN 0.1 AND 500)",
    )
    op.create_check_constraint(
        "request_location",
        "service_requests",
        "(latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL AND latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)",
    )


def downgrade():
    raise RuntimeError("Location data must not be discarded; restore a verified backup instead.")
