"""Allow hall / living-room housing spaces.

Revision ID: 0015
Revises: 0014
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0015"
down_revision: str = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("housing_room_type", "housing_posts", type_="check")
    op.create_check_constraint(
        "housing_room_type", "housing_posts",
        "room_type IN ('SHARED','PRIVATE','HALL','ENTIRE','ANY')",
    )


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM housing_posts WHERE room_type = 'HALL') "
        "THEN RAISE EXCEPTION 'Reclassify hall / living-room housing posts before removing the space option'; "
        "END IF; END $$"
    ))
    op.drop_constraint("housing_room_type", "housing_posts", type_="check")
    op.create_check_constraint(
        "housing_room_type", "housing_posts",
        "room_type IN ('SHARED','PRIVATE','ENTIRE','ANY')",
    )
