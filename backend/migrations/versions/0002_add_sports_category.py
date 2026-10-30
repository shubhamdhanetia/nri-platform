"""Allow Sports community posts.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision: str = "0002"
down_revision: str = "0001"
branch_labels = None
depends_on = None

OLD_CATEGORIES = (
    "'HOUSING', 'RIDES', 'JOBS', 'FOOD', 'EVENTS', 'IMMIGRATION', "
    "'MARKETPLACE', 'MEDICAL_SUPPORT', 'GENERAL'"
)


def upgrade() -> None:
    op.drop_constraint("post_category", "posts", type_="check")
    op.create_check_constraint(
        "post_category", "posts", f"category IN ({OLD_CATEGORIES}, 'SPORTS')"
    )


def downgrade() -> None:
    # PostgreSQL rejects this constraint if Sports rows remain; never rewrite user data.
    op.drop_constraint("post_category", "posts", type_="check")
    op.create_check_constraint(
        "post_category", "posts", f"category IN ({OLD_CATEGORIES})"
    )
