"""Replace the community Rides category with Travel.

Revision ID: 0003
Revises: 0002
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: str = "0002"
branch_labels = None
depends_on = None

OTHER_CATEGORIES = (
    "'HOUSING', 'JOBS', 'FOOD', 'EVENTS', 'SPORTS', 'IMMIGRATION', "
    "'MARKETPLACE', 'MEDICAL_SUPPORT', 'GENERAL'"
)


def upgrade() -> None:
    op.drop_constraint("post_category", "posts", type_="check")
    op.execute(sa.text("UPDATE posts SET category = 'TRAVEL' WHERE category = 'RIDES'"))
    op.create_check_constraint(
        "post_category", "posts", f"category IN ({OTHER_CATEGORIES}, 'TRAVEL')"
    )


def downgrade() -> None:
    op.drop_constraint("post_category", "posts", type_="check")
    op.execute(sa.text("UPDATE posts SET category = 'RIDES' WHERE category = 'TRAVEL'"))
    op.create_check_constraint(
        "post_category", "posts", f"category IN ({OTHER_CATEGORIES}, 'RIDES')"
    )
