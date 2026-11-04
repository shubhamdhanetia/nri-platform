"""Add optional preferred contribution to ride requests.

Revision ID: 0006
Revises: 0005
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: str = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ride_requests",
        sa.Column("preferred_amount", sa.Numeric(6, 2), nullable=True),
    )


def downgrade() -> None:
    # Refuse to silently discard rider preferences during rollback.
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM ride_requests WHERE preferred_amount IS NOT NULL) "
        "THEN RAISE EXCEPTION 'Clear ride preferred amounts before removing the column'; "
        "END IF; END $$"
    ))
    op.drop_column("ride_requests", "preferred_amount")