"""Seed repeatable synthetic data for the implemented Sprint 1 models."""

import calendar
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from apps.core.demo_mocks import MockNotificationOutbox, REQUEST_STATE_SCENARIOS
from apps.donors.models import Appointment, Donation, DonationSlot, DonorProfile
from apps.inventory.models import BloodUnit


BLOOD_GROUPS = ("O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+")
COMPONENTS = tuple(BloodUnit.Component.values)


def birthday_for_age(as_of_date, years):
    year = as_of_date.year - years
    day = min(as_of_date.day, calendar.monthrange(year, as_of_date.month)[1])
    return date(year, as_of_date.month, day)


class Command(BaseCommand):
    help = "Seed synthetic Sprint 1 test records in DEBUG+SQLite only."

    def add_arguments(self, parser):
        parser.add_argument("--as-of-date", type=date.fromisoformat)

    def handle(self, *args, **options):
        if not settings.DEBUG or connection.vendor != "sqlite":
            raise CommandError("Seed data is restricted to DEBUG=True with SQLite.")
        zone = ZoneInfo(settings.BLOOD_BANK_TIME_ZONE)
        as_of_date = options["as_of_date"] or timezone.now().astimezone(zone).date()
        users = []
        profiles = []
        donations = []
        units = []
        slots = []
        appointments = []

        with transaction.atomic():
            for role in ("RECIPIENT", "STAFF", "ADMIN"):
                users.append(self._user(f"seed-{role.lower()}@example.test", role))

            collection_date = as_of_date - timedelta(days=2)
            for index, group in enumerate(BLOOD_GROUPS):
                account = self._user(f"seed-donor-{index}@example.test", "DONOR")
                users.append(account)
                profile, _ = DonorProfile.objects.get_or_create(
                    user=account,
                    defaults={
                        "birth_date": birthday_for_age(as_of_date, 30),
                        "weight_kg": Decimal("62.00"),
                        "blood_group": group,
                        "last_donation_date": collection_date,
                    },
                )
                profiles.append(profile)
                donation, _ = Donation.objects.get_or_create(
                    donor=profile, donation_date=collection_date,
                    defaults={
                        "blood_group": group,
                        "component": Donation.Component.WHOLE_BLOOD,
                        "quantity_units": 1,
                        "screening_weight_kg": Decimal("62.00"),
                    },
                )
                donations.append(donation)
                for component_index, component in enumerate(COMPONENTS):
                    expiry_date = (
                        as_of_date if (index, component_index) == (0, 0)
                        else as_of_date + timedelta(days=1) if (index, component_index) == (0, 1)
                        else as_of_date + timedelta(days=28)
                    )
                    code = f"SEED-{as_of_date:%Y%m%d}-{index}-{component}"
                    unit, _ = BloodUnit.objects.get_or_create(
                        unit_code=code,
                        defaults={
                            "donation": donation,
                            "blood_group": group,
                            "component": component,
                            "collected_at": datetime.combine(collection_date, time(10), tzinfo=zone),
                            "expiry_date": expiry_date,
                            "quantity_units": 1,
                            "status": BloodUnit.Status.EXPIRED if expiry_date <= as_of_date else BloodUnit.Status.AVAILABLE,
                        },
                    )
                    units.append(unit)

            boundaries = (
                ("age", birthday_for_age(as_of_date, 18), Decimal("50.00"), None),
                ("weight", birthday_for_age(as_of_date, 30), Decimal("49.99"), None),
                ("interval", birthday_for_age(as_of_date, 30), Decimal("50.00"), as_of_date - timedelta(days=55)),
            )
            for label, birth_date, weight, last_donation_date in boundaries:
                account = self._user(f"seed-boundary-{label}@example.test", "DONOR")
                users.append(account)
                profile, _ = DonorProfile.objects.get_or_create(
                    user=account,
                    defaults={
                        "birth_date": birth_date,
                        "weight_kg": weight,
                        "blood_group": "O+",
                        "last_donation_date": last_donation_date,
                    },
                )
                profiles.append(profile)

            for offset, status in ((3, Appointment.Status.BOOKED), (4, Appointment.Status.CANCELLED)):
                starts_at = datetime.combine(as_of_date + timedelta(days=offset), time(10), tzinfo=zone)
                slot, _ = DonationSlot.objects.get_or_create(
                    id=uuid5(NAMESPACE_URL, f"bbms-seed-slot-{as_of_date}-{offset}"),
                    defaults={"starts_at": starts_at, "capacity": 1},
                )
                slots.append(slot)
                appointment, _ = Appointment.objects.get_or_create(
                    donor=profiles[-3], slot=slot,
                    defaults={
                        "status": status,
                        "cancelled_at": timezone.now() if status == Appointment.Status.CANCELLED else None,
                    },
                )
                appointments.append(appointment)

        mock_outbox = MockNotificationOutbox()
        for state in REQUEST_STATE_SCENARIOS:
            mock_outbox.enqueue(f"REQUEST_{state}")
        mock_outbox.deliver_pending()
        self.stdout.write(json.dumps({
            "as_of_date": as_of_date.isoformat(),
            "users": len(users),
            "profiles": len(profiles),
            "donations": len(donations),
            "units": len(units),
            "slots": len(slots),
            "appointments": len(appointments),
            "mock_request_states": list(REQUEST_STATE_SCENARIOS),
            "mock_notification_deliveries": len(mock_outbox.adapter.delivered_events),
        }, sort_keys=True))

    @staticmethod
    def _user(email, role):
        User = get_user_model()
        account, _ = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "role": role,
                "first_name": "Synthetic",
                "last_name": role.title(),
                "password": make_password(None),
            },
        )
        if account.role != role:
            raise CommandError("A seed account has an unexpected role.")
        return account
