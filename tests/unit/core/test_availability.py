from datetime import UTC, datetime, timedelta

from apps.core.availability import calculate_availability


def test_availability_excludes_planned_maintenance_and_calculates_target():
    start = datetime(2026, 11, 1, tzinfo=UTC)
    samples = [(start + timedelta(minutes=i), value) for i, value in enumerate((1, 0, 0, 1))]
    report = calculate_availability(
        samples,
        [(start + timedelta(minutes=1), start + timedelta(minutes=3))],
    )

    assert report == {
        "probe_samples": 4,
        "planned_maintenance_samples": 2,
        "included_samples": 2,
        "successful_samples": 2,
        "failed_samples": 0,
        "availability_percent": 100.0,
        "target_percent": 99.5,
        "target_met": True,
    }
