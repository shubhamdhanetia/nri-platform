"""Add optional languages spoken in the household.

Revision ID: 0014
Revises: 0013
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0014"
down_revision: str = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "housing_posts",
        sa.Column("household_languages", sa.JSON(), server_default="[]", nullable=False),
    )


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM housing_posts "
        "WHERE household_languages::jsonb <> '[]'::jsonb) "
        "THEN RAISE EXCEPTION 'Clear household languages before removing the column'; "
        "END IF; END $$"
    ))
    op.drop_column("housing_posts", "household_languages")
