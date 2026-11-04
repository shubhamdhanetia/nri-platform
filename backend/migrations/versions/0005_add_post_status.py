"""Add an independent lifecycle for Community offers and requests.

Revision ID: 0005
Revises: 0004
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: str = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("status", sa.String(6), nullable=False, server_default="ACTIVE"))
    op.create_check_constraint("post_status", "posts", "status IN ('ACTIVE', 'CLOSED')")
    op.create_check_constraint(
        "post_discussion_active", "posts", "status = 'ACTIVE' OR post_type != 'DISCUSSION'"
    )


def downgrade() -> None:
    # Refuse to silently discard a closed post's lifecycle state.
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM posts WHERE status = 'CLOSED') "
        "THEN RAISE EXCEPTION 'Reopen closed posts before removing post status'; "
        "END IF; END $$"
    ))
    op.drop_constraint("post_discussion_active", "posts", type_="check")
    op.drop_constraint("post_status", "posts", type_="check")
    op.drop_column("posts", "status")
