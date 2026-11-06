"""Add the Household Help community category.

Revision ID: 0013
Revises: 0012
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0013"
down_revision: str = "0012"
branch_labels = None
depends_on = None

CATEGORIES = (
    "'HOUSING', 'HOUSEHOLD_HELP', 'TRAVEL', 'PARKING', 'JOBS', 'FOOD', 'EVENTS', 'SPORTS', "
    "'IMMIGRATION', 'MARKETPLACE', 'MEDICAL_SUPPORT', 'GENERAL', 'RIDES_CARPOOL'"
)


def upgrade() -> None:
    op.drop_constraint("post_category", "posts", type_="check")
    op.create_check_constraint("post_category", "posts", f"category IN ({CATEGORIES})")


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM posts WHERE category = 'HOUSEHOLD_HELP') "
        "THEN RAISE EXCEPTION 'Reclassify Household Help posts before removing the category'; "
        "END IF; END $$"
    ))
    op.drop_constraint("post_category", "posts", type_="check")
    op.create_check_constraint(
        "post_category", "posts",
        "category IN ('HOUSING', 'TRAVEL', 'PARKING', 'JOBS', 'FOOD', 'EVENTS', 'SPORTS', "
        "'IMMIGRATION', 'MARKETPLACE', 'MEDICAL_SUPPORT', 'GENERAL', 'RIDES_CARPOOL')",
    )