from datetime import timezone


def iso(dt):
    """ISO 8601 in UTC, like 2026-10-05T09:00:00Z (Hub Contract Rule 6)."""
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
