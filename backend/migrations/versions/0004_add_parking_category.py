"""Allow Parking community posts.

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision: str = "0004"
down_revision: str = "0003"
branch_labels = None
depends_on = None

OLD_CATEGORIES = (
    "'HOUSING', 'TRAVEL', 'JOBS', 'FOOD', 'EVENTS', 'SPORTS', 'IMMIGRATION', "
    "'MARKETPLACE', 'MEDICAL_SUPPORT', 'GENERAL'"
)


def upgrade() -> None:
    op.drop_constraint("post_category", "posts", type_="check")
    op.create_check_constraint(
        "post_category", "posts", f"category IN ({OLD_CATEGORIES}, 'PARKING')"
    )


def downgrade() -> None:
    # Reject rollback while Parking posts remain rather than rewriting user data.
    op.drop_constraint("post_category", "posts", type_="check")
    op.create_check_constraint(
        "post_category", "posts", f"category IN ({OLD_CATEGORIES})"
    )
