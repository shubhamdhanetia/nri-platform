from datetime import datetime, timezone


def utc_now_naive() -> datetime:
    """Use naive UTC consistently with the existing database timestamp columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
