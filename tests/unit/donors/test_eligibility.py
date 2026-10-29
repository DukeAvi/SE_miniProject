from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from django.test import override_settings

from apps.donors.eligibility import check_donor_eligibility


@pytest.mark.parametrize(
    ("birth_date", "on_date", "eligible"),
    [
        (date(2008, 10, 29), date(2026, 10, 28), False),
        (date(2008, 10, 29), date(2026, 10, 29), True),
        (date(2008, 10, 30), date(2026, 10, 29), False),
    ],
)
def test_age_boundary(birth_date, on_date, eligible):
    result = check_donor_eligibility(
        birth_date=birth_date,
        weight_kg=Decimal("50"),
        on_date=on_date,
    )

    assert result.eligible is eligible
    assert ("MINIMUM_AGE" in [rule["rule"] for rule in result.failed_rules]) is not eligible


@pytest.mark.parametrize(
    ("weight", "eligible"), [(Decimal("49.99"), False), (Decimal("50"), True)]
)
def test_weight_boundary(weight, eligible):
    result = check_donor_eligibility(
        birth_date=date(1990, 1, 1),
        weight_kg=weight,
        on_date=date(2026, 10, 29),
    )

    assert result.eligible is eligible


@pytest.mark.parametrize(
    ("days_since_last", "eligible"), [(55, False), (56, True), (57, True)]
)
def test_whole_blood_interval_boundary(days_since_last, eligible):
    result = check_donor_eligibility(
        birth_date=date(1990, 1, 1),
        weight_kg=50,
        on_date=date(2026, 10, 29),
        last_whole_blood_donation=date.fromordinal(
            date(2026, 10, 29).toordinal() - days_since_last
        ),
    )

    assert result.eligible is eligible
    failures = [rule for rule in result.failed_rules if rule["rule"] == "MINIMUM_INTERVAL"]
    if days_since_last == 55:
        assert failures[0]["next_eligible_date"] == "2026-10-30"
    else:
        assert failures == []


def test_returns_all_simultaneous_failures():
    result = check_donor_eligibility(
        birth_date=date(2010, 1, 1),
        weight_kg=45,
        on_date=date(2026, 10, 29),
        last_whole_blood_donation=date(2026, 10, 1),
    )

    assert [item["rule"] for item in result.failed_rules] == [
        "MINIMUM_AGE",
        "MINIMUM_WEIGHT",
        "MINIMUM_INTERVAL",
    ]


def test_non_whole_blood_types_are_excluded_from_demo():
    result = check_donor_eligibility(
        birth_date=date(1990, 1, 1),
        weight_kg=55,
        on_date=date(2026, 10, 29),
        donation_type="PLATELETS",
    )

    assert result.eligible is False
    assert result.failed_rules[0]["rule"] == "DONATION_TYPE"


@override_settings(TIME_ZONE="Asia/Kolkata")
def test_aware_datetime_uses_configured_blood_bank_timezone():
    # 2026-10-28 19:00 UTC is already 2026-10-29 in Asia/Kolkata.
    local_midnight = datetime(2026, 10, 28, 19, 0, tzinfo=timezone.utc)
    result = check_donor_eligibility(
        birth_date=date(2008, 10, 29),
        weight_kg=50,
        on_date=local_midnight,
    )

    assert result.eligible is True


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError, match="include a timezone"):
        check_donor_eligibility(
            birth_date=date(1990, 1, 1),
            weight_kg=50,
            on_date=datetime(2026, 10, 29),
        )
