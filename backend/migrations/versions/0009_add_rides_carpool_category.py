"""Add the informal Rides & carpool Community category.

Revision ID: 0009
Revises: 0008
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0009"
down_revision: str = "0008"
branch_labels = None
depends_on = None

CATEGORIES = (
    "'HOUSING', 'TRAVEL', 'PARKING', 'JOBS', 'FOOD', 'EVENTS', 'SPORTS', "
    "'IMMIGRATION', 'MARKETPLACE', 'MEDICAL_SUPPORT', 'GENERAL', 'RIDES_CARPOOL'"
)


def upgrade() -> None:
    op.drop_constraint("post_category", "posts", type_="check")
    op.create_check_constraint("post_category", "posts", f"category IN ({CATEGORIES})")


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM posts WHERE category = 'RIDES_CARPOOL') "
        "THEN RAISE EXCEPTION 'Reclassify Rides & carpool posts before removing the category'; "
        "END IF; END $$"
    ))
    op.drop_constraint("post_category", "posts", type_="check")
    op.create_check_constraint(
        "post_category", "posts",
        "category IN ('HOUSING', 'TRAVEL', 'PARKING', 'JOBS', 'FOOD', 'EVENTS', 'SPORTS', "
        "'IMMIGRATION', 'MARKETPLACE', 'MEDICAL_SUPPORT', 'GENERAL')",
    )