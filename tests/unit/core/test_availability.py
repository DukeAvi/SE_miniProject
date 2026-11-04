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
        "data_available": True,
    }


def test_availability_does_not_report_success_without_samples():
    report = calculate_availability([], [])

    assert report["probe_samples"] == 0
    assert report["included_samples"] == 0
    assert report["availability_percent"] is None
    assert report["target_met"] is False
    assert report["data_available"] is False


def test_availability_is_unavailable_when_all_samples_are_maintenance():
    start = datetime(2026, 11, 1, tzinfo=UTC)
    report = calculate_availability(
        [(start, 1), (start + timedelta(minutes=1), 0)],
        [(start, start + timedelta(minutes=2))],
    )

    assert report["planned_maintenance_samples"] == 2
    assert report["availability_percent"] is None
    assert report["target_met"] is False
    assert report["data_available"] is False


def test_availability_uses_the_99_5_percent_boundary():
    timestamp = datetime(2026, 11, 1, tzinfo=UTC)
    at_target = calculate_availability([(timestamp, int(index < 199)) for index in range(200)], [])
    below_target = calculate_availability([(timestamp, int(index < 198)) for index in range(200)], [])

    assert at_target["availability_percent"] == 99.5
    assert at_target["target_met"] is True
    assert below_target["availability_percent"] == 99.0
    assert below_target["target_met"] is False
