"""Pure donor-eligibility rules for the classroom demo."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings


MINIMUM_AGE_YEARS = 18
MINIMUM_WEIGHT_KG = Decimal("50")
WHOLE_BLOOD_INTERVAL_DAYS = 56
SUPPORTED_DONATION_TYPES = frozenset({"WHOLE_BLOOD"})


@dataclass(frozen=True)
class EligibilityResult:
    """Eligibility result with every failed rule in API-ready form."""

    eligible: bool
    failed_rules: tuple[dict[str, str], ...]

    def as_dict(self) -> dict[str, object]:
        return {"eligible": self.eligible, "failed_rules": list(self.failed_rules)}


def _local_date(value: date | datetime, timezone_name: str) -> date:
    if isinstance(value, datetime):
        if value.utcoffset() is None:
            raise ValueError("datetime values must include a timezone")
        return value.astimezone(ZoneInfo(timezone_name)).date()
    if isinstance(value, date):
        return value
    raise ValueError("date values are required")


def _age_on(birth_date: date, on_date: date) -> int:
    return on_date.year - birth_date.year - (
        (on_date.month, on_date.day) < (birth_date.month, birth_date.day)
    )


def check_donor_eligibility(
    *,
    birth_date: date,
    weight_kg: Decimal | int | float | str,
    on_date: date | datetime,
    last_whole_blood_donation: date | datetime | None = None,
    donation_type: str = "WHOLE_BLOOD",
    timezone_name: str | None = None,
) -> EligibilityResult:
    """Evaluate every demo eligibility rule on the blood-bank local date.

    Only whole-blood donation is supported in v1.0. The returned interval date
    is inclusive: a donor is interval-eligible on the date 56 days after their
    previous completed whole-blood donation.
    """
    zone_name = timezone_name or settings.TIME_ZONE
    try:
        ZoneInfo(zone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("timezone_name must be a valid IANA time zone") from exc

    appointment_date = _local_date(on_date, zone_name)
    birth_local_date = _local_date(birth_date, zone_name)
    if birth_local_date > appointment_date:
        raise ValueError("birth_date cannot be after the eligibility date")

    try:
        weight = Decimal(str(weight_kg))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("weight_kg must be a valid number") from exc
    if not weight.is_finite() or weight < 0:
        raise ValueError("weight_kg must be a finite, non-negative number")

    failures: list[dict[str, str]] = []
    if donation_type not in SUPPORTED_DONATION_TYPES:
        failures.append(
            {
                "rule": "DONATION_TYPE",
                "message": "Only whole-blood donations are supported in version 1.0.",
            }
        )

    if _age_on(birth_local_date, appointment_date) < MINIMUM_AGE_YEARS:
        failures.append(
            {
                "rule": "MINIMUM_AGE",
                "message": "Donor must be at least 18 years old on the appointment or screening date.",
            }
        )

    if weight < MINIMUM_WEIGHT_KG:
        failures.append(
            {
                "rule": "MINIMUM_WEIGHT",
                "message": "Donor must weigh at least 50 kg at the appointment or screening.",
            }
        )

    if last_whole_blood_donation is not None:
        last_donation_date = _local_date(last_whole_blood_donation, zone_name)
        next_eligible_date = last_donation_date + timedelta(
            days=WHOLE_BLOOD_INTERVAL_DAYS
        )
        if appointment_date < next_eligible_date:
            failures.append(
                {
                    "rule": "MINIMUM_INTERVAL",
                    "message": "At least 56 days must pass between completed whole-blood donations.",
                    "next_eligible_date": next_eligible_date.isoformat(),
                }
            )

    return EligibilityResult(eligible=not failures, failed_rules=tuple(failures))
