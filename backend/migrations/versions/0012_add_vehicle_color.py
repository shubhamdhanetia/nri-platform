"""Add optional vehicle color to driver and ride snapshots.

Revision ID: 0012
Revises: 0011
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0012"
down_revision: str = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("driver_profiles", sa.Column("vehicle_color", sa.String(20), nullable=True))
    op.add_column("ride_offers", sa.Column("vehicle_color", sa.String(20), nullable=True))
    op.add_column("ride_bookings", sa.Column("vehicle_color", sa.String(20), nullable=True))
    op.add_column("carpool_trips", sa.Column("vehicle_color", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("carpool_trips", "vehicle_color")
    op.drop_column("ride_bookings", "vehicle_color")
    op.drop_column("ride_offers", "vehicle_color")
    op.drop_column("driver_profiles", "vehicle_color")