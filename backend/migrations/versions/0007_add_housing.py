"""Add independent housing discovery and inquiries.

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: str = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "housing_posts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("room_type", sa.String(10), nullable=False),
        sa.Column("arrangement", sa.String(12), nullable=False),
        sa.Column("stay_type", sa.String(12), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("area", sa.String(150), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("amount", sa.Numeric(8, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("price_period", sa.String(5), nullable=False),
        sa.Column("available_from", sa.Date(), nullable=False),
        sa.Column("available_until", sa.Date(), nullable=True),
        sa.Column("minimum_stay_days", sa.Integer(), nullable=False),
        sa.Column("furnishing", sa.String(12), nullable=False),
        sa.Column("bathroom", sa.String(12), nullable=False),
        sa.Column("occupants", sa.Integer(), nullable=True),
        sa.Column("available_spaces", sa.Integer(), nullable=False),
        sa.Column("utilities", sa.String(8), nullable=False),
        sa.Column("deposit", sa.Numeric(8, 2), nullable=True),
        sa.Column("fees", sa.Numeric(8, 2), nullable=True),
        sa.Column("approval", sa.String(14), nullable=False),
        sa.Column("kitchen", sa.String(14), nullable=False),
        sa.Column("smoking", sa.String(12), nullable=False),
        sa.Column("alcohol", sa.String(12), nullable=False),
        sa.Column("pets", sa.String(12), nullable=False),
        sa.Column("parking", sa.Boolean(), nullable=True),
        sa.Column("laundry", sa.Boolean(), nullable=True),
        sa.Column("kitchen_access", sa.Boolean(), nullable=True),
        sa.Column("work_from_home", sa.Boolean(), nullable=True),
        sa.Column("household_notes", sa.Text(), nullable=False),
        sa.Column("accessibility_notes", sa.Text(), nullable=False),
        sa.Column("photo_urls", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(8), nullable=False, server_default="ACTIVE"),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("kind IN ('LISTING','REQUEST','TOGETHER')", name="housing_kind"),
        sa.CheckConstraint("status IN ('ACTIVE','FILLED','ARCHIVED')", name="housing_status"),
        sa.CheckConstraint("room_type IN ('SHARED','PRIVATE','ENTIRE','ANY')", name="housing_room_type"),
        sa.CheckConstraint("arrangement IN ('HOUSEHOLD','RENTAL','SUBLET','TAKEOVER','ANY')", name="housing_arrangement"),
        sa.CheckConstraint("kind != 'LISTING' OR (room_type != 'ANY' AND arrangement != 'ANY')", name="housing_listing_space"),
        sa.CheckConstraint("stay_type IN ('SHORT_TERM','LONG_TERM','FLEXIBLE')", name="housing_stay"),
        sa.CheckConstraint("price_period IN ('MONTH','WEEK','NIGHT')", name="housing_period"),
        sa.CheckConstraint("amount >= 0 AND (deposit IS NULL OR deposit >= 0) AND (fees IS NULL OR fees >= 0)", name="housing_amounts"),
        sa.CheckConstraint("available_until IS NULL OR available_until >= available_from", name="housing_dates"),
        sa.CheckConstraint("minimum_stay_days BETWEEN 1 AND 3650 AND available_spaces BETWEEN 1 AND 20 AND (occupants IS NULL OR occupants BETWEEN 0 AND 50)", name="housing_occupancy"),
        sa.CheckConstraint("furnishing IN ('FURNISHED','PARTLY','UNFURNISHED','UNSPECIFIED')", name="housing_furnishing"),
        sa.CheckConstraint("bathroom IN ('PRIVATE','SHARED','UNSPECIFIED')", name="housing_bathroom"),
        sa.CheckConstraint("utilities IN ('INCLUDED','EXTRA','PARTLY','UNKNOWN')", name="housing_utilities"),
        sa.CheckConstraint("approval IN ('NOT_APPLICABLE','REQUIRED','PENDING','OBTAINED')", name="housing_approval"),
        sa.CheckConstraint("arrangement NOT IN ('SUBLET','TAKEOVER') OR approval != 'NOT_APPLICABLE'", name="housing_transfer_approval"),
        sa.CheckConstraint("kitchen IN ('VEGETARIAN','EGGS_ALLOWED','UNRESTRICTED','UNSPECIFIED')", name="housing_kitchen"),
        sa.CheckConstraint("smoking IN ('NO','OUTSIDE','YES','UNSPECIFIED')", name="housing_smoking"),
        sa.CheckConstraint("alcohol IN ('NO','YES','UNSPECIFIED')", name="housing_alcohol"),
        sa.CheckConstraint("pets IN ('NO','ALLOWED','PRESENT','UNSPECIFIED')", name="housing_pets"),
    )
    op.create_index("ix_housing_discovery", "housing_posts", ["status", "is_private", "expires_at", "created_at", "id"])
    op.create_index("ix_housing_owner_created", "housing_posts", ["owner_id", "created_at", "id"])
    op.create_index("ix_housing_city", "housing_posts", ["city"])
    op.create_table(
        "housing_saves",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("housing_id", sa.Uuid(), sa.ForeignKey("housing_posts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "housing_inquiries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("housing_id", sa.Uuid(), sa.ForeignKey("housing_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("housing_id", "sender_id", name="uq_housing_inquiry_sender"),
    )
    op.create_index("ix_housing_inquiries_housing_id", "housing_inquiries", ["housing_id"])
    op.create_index("ix_housing_inquiry_sender", "housing_inquiries", ["sender_id", "created_at", "id"])
    op.create_table(
        "housing_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("inquiry_id", sa.Uuid(), sa.ForeignKey("housing_inquiries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_housing_messages_inquiry_id", "housing_messages", ["inquiry_id"])
    op.create_table(
        "housing_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("housing_id", sa.Uuid(), sa.ForeignKey("housing_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reporter_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.String(14), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("housing_id", "reporter_id", name="uq_housing_report_user"),
        sa.CheckConstraint("reason IN ('SCAM','INACCURATE','DISCRIMINATION','OTHER')", name="housing_report_reason"),
    )
    op.create_index("ix_housing_reports_housing_id", "housing_reports", ["housing_id"])


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM housing_posts) "
        "THEN RAISE EXCEPTION 'Export and explicitly remove housing data before removing Housing'; "
        "END IF; END $$"
    ))
    for table in ("housing_reports", "housing_messages", "housing_inquiries", "housing_saves", "housing_posts"):
        op.drop_table(table)
