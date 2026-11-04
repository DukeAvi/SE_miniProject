from datetime import UTC, datetime

from scripts.backup_scheduler import next_backup_time


def test_daily_backup_is_scheduled_for_0200_utc():
    assert next_backup_time(datetime(2026, 11, 4, 1, 59, tzinfo=UTC)) == datetime(
        2026, 11, 4, 2, 0, tzinfo=UTC
    )
    assert next_backup_time(datetime(2026, 11, 4, 2, 0, tzinfo=UTC)) == datetime(
        2026, 11, 4, 2, 0, tzinfo=UTC
    )
    assert next_backup_time(datetime(2026, 11, 4, 2, 1, tzinfo=UTC)) == datetime(2026, 11, 4, 2, 1, tzinfo=UTC)
    assert next_backup_time(
        datetime(2026, 11, 4, 2, 1, tzinfo=UTC), datetime(2026, 11, 4, 2, 0, tzinfo=UTC)
    ) == datetime(2026, 11, 5, 2, 0, tzinfo=UTC)
