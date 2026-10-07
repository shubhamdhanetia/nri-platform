from datetime import datetime, timedelta, timezone


EDIT_WINDOW = timedelta(minutes=30)


class EditWindowExpiredError(Exception):
    pass


def is_within_edit_window(created_at: datetime) -> bool:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    else:
        created_at = created_at.astimezone(timezone.utc)

    elapsed = datetime.now(timezone.utc) - created_at
    return timedelta(0) <= elapsed < EDIT_WINDOW
