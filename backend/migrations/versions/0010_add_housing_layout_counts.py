"""Add optional Housing bedroom and bathroom counts.

Revision ID: 0010
Revises: 0009
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: str = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("housing_posts", sa.Column("bedroom_count", sa.Integer(), nullable=True))
    op.add_column("housing_posts", sa.Column("bathroom_count", sa.Numeric(3, 1), nullable=True))
    op.create_check_constraint(
        "housing_bedroom_count", "housing_posts",
        "bedroom_count IS NULL OR bedroom_count BETWEEN 0 AND 20",
    )
    op.create_check_constraint(
        "housing_bathroom_count", "housing_posts",
        "bathroom_count IS NULL OR bathroom_count BETWEEN 0.5 AND 20",
    )


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM housing_posts "
        "WHERE bedroom_count IS NOT NULL OR bathroom_count IS NOT NULL) "
        "THEN RAISE EXCEPTION 'Clear Housing layout counts before removing the columns'; "
        "END IF; END $$"
    ))
    op.drop_constraint("housing_bathroom_count", "housing_posts", type_="check")
    op.drop_constraint("housing_bedroom_count", "housing_posts", type_="check")
    op.drop_column("housing_posts", "bathroom_count")
    op.drop_column("housing_posts", "bedroom_count")