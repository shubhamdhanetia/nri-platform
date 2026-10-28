from sqlalchemy import Engine, insert, literal, select, text

from app.models.carpool import CarpoolNotification
from app.models.notification import Notification


def migrate_carpool_notifications(engine: Engine) -> None:
    legacy = CarpoolNotification.__table__
    notifications = Notification.__table__
    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            # Serialize startup copies across API workers without locking user tables.
            connection.execute(text("SELECT pg_advisory_xact_lock(742801934)"))
        missing = ~select(notifications.c.id).where(
            notifications.c.legacy_carpool_id == legacy.c.id,
        ).exists()
        connection.execute(insert(notifications).from_select(
            ["user_id", "category", "event_type", "resource_id", "target_path",
             "message", "is_read", "created_at", "legacy_carpool_id"],
            select(
                legacy.c.user_id, literal("carpool"), literal("carpool.legacy"),
                legacy.c.trip_id, literal("/rides/carpools/") + legacy.c.trip_id.cast(notifications.c.target_path.type),
                legacy.c.message, legacy.c.is_read, legacy.c.created_at, legacy.c.id,
            ).where(missing),
        ))
