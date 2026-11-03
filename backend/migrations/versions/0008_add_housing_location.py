"""Add resolved Housing locations and H3 lookup.

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa

revision: str = "0008"
down_revision: str = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in (
        sa.Column("location_id", sa.String(200), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("h3_cell_id", sa.String(15), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(30), nullable=True),
    ):
        op.add_column("housing_posts", column)
    op.create_index("ix_housing_posts_h3_cell_id", "housing_posts", ["h3_cell_id"])
    op.create_check_constraint(
        "housing_location_complete", "housing_posts",
        "(location_id IS NULL AND location IS NULL AND latitude IS NULL AND longitude IS NULL "
        "AND h3_cell_id IS NULL AND state IS NULL AND postal_code IS NULL) OR "
        "(location_id IS NOT NULL AND location IS NOT NULL AND latitude IS NOT NULL AND longitude IS NOT NULL "
        "AND h3_cell_id IS NOT NULL AND state IS NOT NULL AND postal_code IS NOT NULL "
        "AND latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)",
    )


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM housing_posts WHERE location_id IS NOT NULL) "
        "THEN RAISE EXCEPTION 'Export and explicitly clear Housing locations before removing map search'; "
        "END IF; END $$"
    ))
    op.drop_constraint("housing_location_complete", "housing_posts", type_="check")
    op.drop_index("ix_housing_posts_h3_cell_id", table_name="housing_posts")
    for column in ("postal_code", "state", "h3_cell_id", "longitude", "latitude", "location", "location_id"):
        op.drop_column("housing_posts", column)
