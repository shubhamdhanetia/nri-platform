"""Initial application schema

Revision ID: 0001
Revises: 
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('picture', sa.String(length=500), nullable=True),
    sa.Column('provider', sa.String(length=50), nullable=False),
    sa.Column('provider_id', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('bio', sa.String(length=160), nullable=True),
    sa.Column('home_city', sa.String(length=100), nullable=True),
    sa.Column('languages', sa.JSON(), server_default='[]', nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('provider_id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_table('carpool_trips',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('driver_id', sa.Uuid(), nullable=False),
    sa.Column('outbound_id', sa.Uuid(), nullable=True),
    sa.Column('pickup', sa.JSON(), nullable=False),
    sa.Column('dropoff', sa.JSON(), nullable=False),
    sa.Column('pickup_start', sa.DateTime(), nullable=False),
    sa.Column('pickup_end', sa.DateTime(), nullable=False),
    sa.Column('timezone', sa.String(length=100), nullable=False),
    sa.Column('seats', sa.Integer(), nullable=False),
    sa.Column('bags_per_person', sa.Integer(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=6, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('vehicle', sa.String(length=100), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('cancellation_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("status IN ('OPEN','CANCELLED')"),
    sa.CheckConstraint('amount >= 0'),
    sa.CheckConstraint('bags_per_person BETWEEN 0 AND 10'),
    sa.CheckConstraint('pickup_end >= pickup_start'),
    sa.CheckConstraint('seats BETWEEN 1 AND 8'),
    sa.ForeignKeyConstraint(['driver_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['outbound_id'], ['carpool_trips.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('outbound_id')
    )
    op.create_index(op.f('ix_carpool_trips_driver_id'), 'carpool_trips', ['driver_id'], unique=False)
    op.create_index('ix_carpool_trips_dropoff_h3', 'carpool_trips', [sa.literal_column("(CAST(dropoff ->> 'h3_cell_id' AS VARCHAR))")], unique=False)
    op.create_index('ix_carpool_trips_pickup_h3', 'carpool_trips', [sa.literal_column("(CAST(pickup ->> 'h3_cell_id' AS VARCHAR))")], unique=False)
    op.create_index(op.f('ix_carpool_trips_pickup_start'), 'carpool_trips', ['pickup_start'], unique=False)
    op.create_index(op.f('ix_carpool_trips_status'), 'carpool_trips', ['status'], unique=False)
    op.create_table('driver_profiles',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('vehicle', sa.String(length=100), nullable=False),
    sa.Column('passenger_capacity', sa.Integer(), nullable=False),
    sa.Column('phone', sa.String(length=30), nullable=False),
    sa.Column('acknowledgement_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('passenger_capacity BETWEEN 1 AND 8'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('notifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('event_type', sa.String(length=100), nullable=False),
    sa.Column('resource_id', sa.Uuid(), nullable=False),
    sa.Column('target_path', sa.String(length=300), nullable=False),
    sa.Column('message', sa.String(length=500), nullable=False),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_user_created_id', 'notifications', ['user_id', 'created_at', 'id'], unique=False)
    op.create_index('ix_notifications_user_read', 'notifications', ['user_id', 'is_read'], unique=False)
    op.create_table('posts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('category', sa.Enum('HOUSING', 'RIDES', 'JOBS', 'FOOD', 'EVENTS', 'IMMIGRATION', 'MARKETPLACE', 'MEDICAL_SUPPORT', 'GENERAL', name='post_category', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('post_type', sa.Enum('OFFER', 'REQUEST', 'DISCUSSION', name='post_type', native_enum=False, create_constraint=True), server_default='OFFER', nullable=False),
    sa.Column('is_private', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('location_id', sa.String(length=200), nullable=False),
    sa.Column('location', sa.Text(), nullable=False),
    sa.Column('country_code', sa.String(length=2), nullable=False),
    sa.Column('postal_code', sa.String(length=20), nullable=False),
    sa.Column('state', sa.String(length=10), nullable=False),
    sa.Column('city', sa.String(length=100), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('h3_cell_id', sa.String(length=20), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_posts_h3_cell_id'), 'posts', ['h3_cell_id'], unique=False)
    op.create_index(op.f('ix_posts_id'), 'posts', ['id'], unique=False)
    op.create_table('ride_requests',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('rider_id', sa.Uuid(), nullable=False),
    sa.Column('pickup', sa.JSON(), nullable=False),
    sa.Column('dropoff', sa.JSON(), nullable=False),
    sa.Column('pickup_start', sa.DateTime(), nullable=False),
    sa.Column('pickup_end', sa.DateTime(), nullable=False),
    sa.Column('timezone', sa.String(length=100), nullable=False),
    sa.Column('passengers', sa.Integer(), nullable=False),
    sa.Column('bags', sa.Integer(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('rider_phone', sa.String(length=30), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("status IN ('OPEN','CONFIRMED','CANCELLED','EXPIRED')"),
    sa.CheckConstraint('bags BETWEEN 0 AND 10'),
    sa.CheckConstraint('passengers BETWEEN 1 AND 8'),
    sa.CheckConstraint('pickup_end >= pickup_start'),
    sa.ForeignKeyConstraint(['rider_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ride_requests_pickup_h3', 'ride_requests', [sa.literal_column("(CAST(pickup ->> 'h3_cell_id' AS VARCHAR))")], unique=False)
    op.create_index(op.f('ix_ride_requests_pickup_start'), 'ride_requests', ['pickup_start'], unique=False)
    op.create_index(op.f('ix_ride_requests_rider_id'), 'ride_requests', ['rider_id'], unique=False)
    op.create_index(op.f('ix_ride_requests_status'), 'ride_requests', ['status'], unique=False)
    op.create_index('ix_ride_requests_status_pickup_id', 'ride_requests', ['status', 'pickup_start', 'id'], unique=False)
    op.create_table('carpool_seat_requests',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('trip_id', sa.Uuid(), nullable=False),
    sa.Column('rider_id', sa.Uuid(), nullable=False),
    sa.Column('passengers', sa.Integer(), nullable=False),
    sa.Column('bags', sa.Integer(), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('rider_phone', sa.String(length=30), nullable=False),
    sa.Column('driver_phone', sa.String(length=30), nullable=True),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('cancellation_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("status IN ('PENDING','CONFIRMED','DECLINED','CANCELLED')"),
    sa.CheckConstraint('bags BETWEEN 0 AND 80'),
    sa.CheckConstraint('passengers BETWEEN 1 AND 8'),
    sa.ForeignKeyConstraint(['rider_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['trip_id'], ['carpool_trips.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('trip_id', 'rider_id', name='uq_carpool_trip_rider')
    )
    op.create_index(op.f('ix_carpool_seat_requests_rider_id'), 'carpool_seat_requests', ['rider_id'], unique=False)
    op.create_index(op.f('ix_carpool_seat_requests_trip_id'), 'carpool_seat_requests', ['trip_id'], unique=False)
    op.create_table('comments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('post_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_comments_id'), 'comments', ['id'], unique=False)
    op.create_index(op.f('ix_comments_post_id'), 'comments', ['post_id'], unique=False)
    op.create_index(op.f('ix_comments_user_id'), 'comments', ['user_id'], unique=False)
    op.create_table('post_reactions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('post_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('reaction', sa.Enum('LIKE', 'DISLIKE', name='post_reaction_type', native_enum=False, create_constraint=True), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('post_id', 'user_id', name='uq_post_reactions_post_user')
    )
    op.create_index(op.f('ix_post_reactions_id'), 'post_reactions', ['id'], unique=False)
    op.create_index(op.f('ix_post_reactions_post_id'), 'post_reactions', ['post_id'], unique=False)
    op.create_index(op.f('ix_post_reactions_user_id'), 'post_reactions', ['user_id'], unique=False)
    op.create_table('ride_offers',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('request_id', sa.Uuid(), nullable=False),
    sa.Column('driver_id', sa.Uuid(), nullable=False),
    sa.Column('pickup_time', sa.DateTime(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=6, scale=2), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('vehicle', sa.String(length=100), nullable=False),
    sa.Column('passenger_capacity', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("status IN ('PENDING','ACCEPTED','WITHDRAWN','NOT_SELECTED','EXPIRED')"),
    sa.CheckConstraint('amount >= 0'),
    sa.ForeignKeyConstraint(['driver_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['request_id'], ['ride_requests.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('request_id', 'driver_id', name='uq_ride_offer_driver')
    )
    op.create_index(op.f('ix_ride_offers_driver_id'), 'ride_offers', ['driver_id'], unique=False)
    op.create_index(op.f('ix_ride_offers_request_id'), 'ride_offers', ['request_id'], unique=False)
    op.create_table('saved_posts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('post_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('saved_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('post_id', 'user_id', name='uq_saved_posts_post_user')
    )
    op.create_index(op.f('ix_saved_posts_id'), 'saved_posts', ['id'], unique=False)
    op.create_index(op.f('ix_saved_posts_post_id'), 'saved_posts', ['post_id'], unique=False)
    op.create_index(op.f('ix_saved_posts_user_id'), 'saved_posts', ['user_id'], unique=False)
    op.create_table('ride_bookings',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('request_id', sa.Uuid(), nullable=False),
    sa.Column('offer_id', sa.Uuid(), nullable=False),
    sa.Column('rider_id', sa.Uuid(), nullable=False),
    sa.Column('driver_id', sa.Uuid(), nullable=False),
    sa.Column('driver_phone', sa.String(length=30), nullable=False),
    sa.Column('rider_phone', sa.String(length=30), nullable=False),
    sa.Column('vehicle', sa.String(length=100), nullable=False),
    sa.Column('pickup_time', sa.DateTime(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=6, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('cancellation_reason', sa.Text(), nullable=True),
    sa.Column('cancelled_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("status IN ('CONFIRMED','COMPLETED','CANCELLED')"),
    sa.ForeignKeyConstraint(['cancelled_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['driver_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['offer_id'], ['ride_offers.id'], ),
    sa.ForeignKeyConstraint(['request_id'], ['ride_requests.id'], ),
    sa.ForeignKeyConstraint(['rider_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('offer_id'),
    sa.UniqueConstraint('request_id')
    )
    op.create_index(op.f('ix_ride_bookings_driver_id'), 'ride_bookings', ['driver_id'], unique=False)
    op.create_index(op.f('ix_ride_bookings_rider_id'), 'ride_bookings', ['rider_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ride_bookings_rider_id'), table_name='ride_bookings')
    op.drop_index(op.f('ix_ride_bookings_driver_id'), table_name='ride_bookings')
    op.drop_table('ride_bookings')
    op.drop_index(op.f('ix_saved_posts_user_id'), table_name='saved_posts')
    op.drop_index(op.f('ix_saved_posts_post_id'), table_name='saved_posts')
    op.drop_index(op.f('ix_saved_posts_id'), table_name='saved_posts')
    op.drop_table('saved_posts')
    op.drop_index(op.f('ix_ride_offers_request_id'), table_name='ride_offers')
    op.drop_index(op.f('ix_ride_offers_driver_id'), table_name='ride_offers')
    op.drop_table('ride_offers')
    op.drop_index(op.f('ix_post_reactions_user_id'), table_name='post_reactions')
    op.drop_index(op.f('ix_post_reactions_post_id'), table_name='post_reactions')
    op.drop_index(op.f('ix_post_reactions_id'), table_name='post_reactions')
    op.drop_table('post_reactions')
    op.drop_index(op.f('ix_comments_user_id'), table_name='comments')
    op.drop_index(op.f('ix_comments_post_id'), table_name='comments')
    op.drop_index(op.f('ix_comments_id'), table_name='comments')
    op.drop_table('comments')
    op.drop_index(op.f('ix_carpool_seat_requests_trip_id'), table_name='carpool_seat_requests')
    op.drop_index(op.f('ix_carpool_seat_requests_rider_id'), table_name='carpool_seat_requests')
    op.drop_table('carpool_seat_requests')
    op.drop_index('ix_ride_requests_status_pickup_id', table_name='ride_requests')
    op.drop_index(op.f('ix_ride_requests_status'), table_name='ride_requests')
    op.drop_index(op.f('ix_ride_requests_rider_id'), table_name='ride_requests')
    op.drop_index(op.f('ix_ride_requests_pickup_start'), table_name='ride_requests')
    op.drop_index('ix_ride_requests_pickup_h3', table_name='ride_requests')
    op.drop_table('ride_requests')
    op.drop_index(op.f('ix_posts_id'), table_name='posts')
    op.drop_index(op.f('ix_posts_h3_cell_id'), table_name='posts')
    op.drop_table('posts')
    op.drop_index('ix_notifications_user_read', table_name='notifications')
    op.drop_index('ix_notifications_user_created_id', table_name='notifications')
    op.drop_table('notifications')
    op.drop_table('driver_profiles')
    op.drop_index(op.f('ix_carpool_trips_status'), table_name='carpool_trips')
    op.drop_index(op.f('ix_carpool_trips_pickup_start'), table_name='carpool_trips')
    op.drop_index('ix_carpool_trips_pickup_h3', table_name='carpool_trips')
    op.drop_index('ix_carpool_trips_dropoff_h3', table_name='carpool_trips')
    op.drop_index(op.f('ix_carpool_trips_driver_id'), table_name='carpool_trips')
    op.drop_table('carpool_trips')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
