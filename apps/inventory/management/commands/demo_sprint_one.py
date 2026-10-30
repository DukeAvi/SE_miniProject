"""Run a synthetic, end-to-end Sprint 1 API demonstration."""

from datetime import datetime, time, timedelta
from secrets import token_urlsafe
import subprocess
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.donors.models import DonationSlot, DonorProfile


class Command(BaseCommand):
    help = "Demonstrate Sprint 1 API flows with isolated synthetic data (DEBUG + SQLite only)."

    def handle(self, *args, **options):
        if not settings.DEBUG or connection.vendor != "sqlite":
            raise CommandError("The demo is restricted to DEBUG=True with SQLite; never run against production data.")

        run_id = uuid4().hex[:10]
        password = token_urlsafe(24)
        today = timezone.localdate(timezone=ZoneInfo(settings.BLOOD_BANK_TIME_ZONE))
        donor = self._user("DONOR", run_id, password)
        staff = self._user("STAFF", run_id, password)
        recipient = self._user("RECIPIENT", run_id, password)
        DonorProfile.objects.create(
            user=donor,
            birth_date=today - timedelta(days=30 * 365),
            weight_kg="62.00",
            blood_group="O+",
        )
        slot_date = today + timedelta(days=3)
        slot = DonationSlot.objects.create(
            starts_at=datetime.combine(slot_date, time(10), tzinfo=ZoneInfo(settings.BLOOD_BANK_TIME_ZONE)),
            capacity=3,
        )

        self.stdout.write("BBMS Sprint 1 product demonstration | synthetic local data")
        try:
            revision = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            revision = "unavailable"
        self.stdout.write(f"Tested revision: {revision}")
        self.stdout.write(f"Blood-bank date: {today.isoformat()} | timezone: {settings.BLOOD_BANK_TIME_ZONE}")

        donor_client = APIClient(enforce_csrf_checks=True)
        self._login(donor_client, donor, password)
        slots = donor_client.get("/api/v1/donation-slots", {"date": slot_date.isoformat()})
        self._expect(slots.status_code == 200, "Donor views available appointment slots")
        booking = donor_client.post(
            "/api/v1/donors/me/appointments",
            {"slot_id": str(slot.pk)},
            format="json",
            HTTP_X_CSRFTOKEN=self._csrf(donor_client),
        )
        self._expect(booking.status_code == 201, "Donor books a slot")
        self.stdout.write(f"  Appointment status: {booking.json()['status']}")
        self._logout(donor_client)

        staff_client = APIClient(enforce_csrf_checks=True)
        self._login(staff_client, staff, password)
        donation = staff_client.post(
            "/api/v1/donations",
            {
                "donor_id": donor.pk,
                "donation_date": today.isoformat(),
                "blood_group": "O+",
                "component": "WHOLE_BLOOD",
                "quantity_units": 1,
                "status": "COMPLETED",
                "screening_weight_kg": "62.00",
            },
            format="json",
            HTTP_X_CSRFTOKEN=self._csrf(staff_client),
        )
        self._expect(donation.status_code == 201, "Staff records a completed donation")
        donation_id = donation.json()["id"]
        unit_code = f"BB-DEMO-{today:%Y%m%d}-{run_id.upper()}"
        unit = staff_client.post(
            "/api/v1/inventory/units",
            {
                "unit_code": unit_code,
                "donation_id": donation_id,
                "blood_group": "O+",
                "component": "RBC",
                "collected_at": datetime.combine(today, time(11), tzinfo=ZoneInfo(settings.BLOOD_BANK_TIME_ZONE)).isoformat(),
                "expiry_date": (today + timedelta(days=28)).isoformat(),
                "quantity_units": 1,
            },
            format="json",
            HTTP_X_CSRFTOKEN=self._csrf(staff_client),
        )
        self._expect(unit.status_code == 201, "Staff creates a verified inventory unit")
        found = staff_client.get(
            "/api/v1/inventory/units",
            {"blood_group": "O+", "component": "RBC", "status": "AVAILABLE", "page": 1, "page_size": 5},
        )
        self._expect(found.status_code == 200, "Staff searches inventory")
        self.stdout.write(f"  Unit code: {unit.json()['unit_code']} | status: {unit.json()['status']}")
        self._logout(staff_client)

        recipient_client = APIClient(enforce_csrf_checks=True)
        self._login(recipient_client, recipient, password)
        availability = recipient_client.get(
            "/api/v1/inventory/availability",
            {"blood_group": "O+", "component": "RBC"},
        )
        self._expect(availability.status_code == 200, "Recipient views aggregate availability")
        self._expect("unit_code" not in availability.json(), "Recipient response excludes unit identifiers")
        self.stdout.write(
            f"  Recipient aggregate: {availability.json()['available_units']} available | "
            f"nearest expiry: {availability.json()['nearest_expiry']}"
        )
        self._logout(recipient_client)
        self.stdout.write(self.style.SUCCESS("PASS: login, booking, donation recording, inventory creation/search, aggregate availability, and logout"))

    def _user(self, role, run_id, password):
        email = f"demo-{role.lower()}-{run_id}@example.test"
        return get_user_model().objects.create_user(
            username=email,
            email=email,
            first_name="Synthetic",
            last_name=role.title(),
            password=password,
            role=role,
        )

    def _csrf(self, client):
        response = client.get("/api/v1/auth/csrf")
        self._expect(response.status_code == 200, "CSRF bootstrap")
        return response.json()["csrfToken"]

    def _login(self, client, user, password):
        response = client.post(
            "/api/v1/auth/login",
            {"email": user.email, "password": password},
            format="json",
            HTTP_X_CSRFTOKEN=self._csrf(client),
        )
        self._expect(response.status_code == 200, f"{user.role} session login")

    def _logout(self, client):
        response = client.post(
            "/api/v1/auth/logout",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=self._csrf(client),
        )
        self._expect(response.status_code == 204, "Session logout")

    def _expect(self, passed, message):
        if not passed:
            raise CommandError(f"Demo step failed: {message}.")
        self.stdout.write(self.style.SUCCESS(f"PASS: {message}"))
