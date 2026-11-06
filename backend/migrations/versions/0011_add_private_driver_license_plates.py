"""Add private driver plate snapshots for confirmed bookings.

Revision ID: 0011
Revises: 0010
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: str = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("driver_profiles", sa.Column("license_plate", sa.String(20), nullable=True))
    op.add_column("ride_offers", sa.Column("driver_license_plate", sa.String(20), nullable=True))
    op.add_column("ride_bookings", sa.Column("driver_license_plate", sa.String(20), nullable=True))
    op.add_column("carpool_trips", sa.Column("driver_license_plate", sa.String(20), nullable=True))
    op.add_column("carpool_seat_requests", sa.Column("driver_license_plate", sa.String(20), nullable=True))


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM driver_profiles WHERE license_plate IS NOT NULL) "
        "OR EXISTS (SELECT 1 FROM ride_offers WHERE driver_license_plate IS NOT NULL) "
        "OR EXISTS (SELECT 1 FROM ride_bookings WHERE driver_license_plate IS NOT NULL) "
        "OR EXISTS (SELECT 1 FROM carpool_trips WHERE driver_license_plate IS NOT NULL) "
        "OR EXISTS (SELECT 1 FROM carpool_seat_requests WHERE driver_license_plate IS NOT NULL) "
        "THEN RAISE EXCEPTION 'Clear private license plate data before removing its columns'; "
        "END IF; END $$"
    ))
    op.drop_column("carpool_seat_requests", "driver_license_plate")
    op.drop_column("carpool_trips", "driver_license_plate")
    op.drop_column("ride_bookings", "driver_license_plate")
    op.drop_column("ride_offers", "driver_license_plate")
    op.drop_column("driver_profiles", "license_plate")