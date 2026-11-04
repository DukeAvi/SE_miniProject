"""Seed a deterministic, synthetic PostgreSQL workload for TC-Perf-01."""

import argparse
from datetime import datetime, time, timedelta
import json
import os
from pathlib import Path
import secrets
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bbms.settings")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


ROW_COUNT = 10_000
DONOR_COUNT = 100
BLOOD_GROUPS = ("O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-")
COMPONENTS = ("WHOLE_BLOOD", "RBC", "PLASMA", "PLATELETS")


def seed(credentials_path: Path) -> None:
    if os.environ.get("PERF_BENCHMARK_CONFIRM") != "yes":
        raise SystemExit("Set PERF_BENCHMARK_CONFIRM=yes to allow synthetic benchmark data creation.")

    import django

    django.setup()

    from django.contrib.auth import get_user_model
    from django.db import connection, transaction
    from django.utils import timezone

    from apps.accounts.models import AccountRole
    from apps.donors.models import Donation, DonorProfile
    from apps.inventory.models import BloodUnit

    User = get_user_model()
    if User.objects.filter(email="perf-staff@example.test").exists():
        raise SystemExit("Performance seed account already exists; use a clean benchmark database.")

    today = timezone.localdate()
    password = secrets.token_urlsafe(32)
    with transaction.atomic():
        staff = User.objects.create_user(
            username="perf-staff",
            email="perf-staff@example.test",
            password=password,
            role=AccountRole.STAFF,
        )
        donor_users = [
            User(
                username=f"perf-donor-{index:03d}",
                email=f"perf-donor-{index:03d}@example.test",
                role=AccountRole.DONOR,
                password="!",
            )
            for index in range(DONOR_COUNT)
        ]
        User.objects.bulk_create(donor_users, batch_size=500)
        donor_users = list(User.objects.filter(username__startswith="perf-donor-").order_by("username"))
        donors = [
            DonorProfile(
                user=user,
                birth_date=today - timedelta(days=30 * 365),
                weight_kg="65.00",
                blood_group=BLOOD_GROUPS[index % len(BLOOD_GROUPS)],
            )
            for index, user in enumerate(donor_users)
        ]
        DonorProfile.objects.bulk_create(donors, batch_size=500)
        donors = list(DonorProfile.objects.order_by("user__username"))

        donations = [
            Donation(
                donor=donors[index % DONOR_COUNT],
                donation_date=today - timedelta(days=index % 120),
                blood_group=BLOOD_GROUPS[index % len(BLOOD_GROUPS)],
                component=COMPONENTS[index % len(COMPONENTS)],
                quantity_units=1 + index % 3,
                status=Donation.Status.COMPLETED,
                screening_weight_kg="65.00",
            )
            for index in range(ROW_COUNT)
        ]
        Donation.objects.bulk_create(donations, batch_size=1000)
        donations = list(Donation.objects.order_by("donation_date", "id").values("id", "donation_date"))
        units = []
        for index, donation in enumerate(donations):
            donation_date = donation["donation_date"]
            units.append(
                BloodUnit(
                    donation_id=donation["id"],
                    unit_code=f"PERF-{index:05d}",
                    blood_group=BLOOD_GROUPS[index % len(BLOOD_GROUPS)],
                    component=COMPONENTS[(index // len(BLOOD_GROUPS)) % len(COMPONENTS)],
                    collected_at=timezone.make_aware(datetime.combine(donation_date, time(12))),
                    expiry_date=donation_date + timedelta(days=90),
                    quantity_units=1,
                    status=(
                        BloodUnit.Status.AVAILABLE
                        if index % 10 != 0
                        else BloodUnit.Status.RESERVED
                    ),
                )
            )
        BloodUnit.objects.bulk_create(units, batch_size=1000)

    with connection.cursor() as cursor:
        cursor.execute("ANALYZE donors_donation")
        cursor.execute("ANALYZE inventory_bloodunit")
    matching_units = BloodUnit.objects.filter(
        status=BloodUnit.Status.AVAILABLE,
        blood_group="O+",
        component=BloodUnit.Component.RBC,
        expiry_date__gt=today,
    ).count()
    if matching_units < 100:
        raise RuntimeError("The synthetic inventory seed did not produce a full 100-row search page.")

    credentials_path.parent.mkdir(parents=True, exist_ok=True)
    credentials_path.write_text(
        json.dumps(
            {
                "email": staff.email,
                "password": password,
                "from_date": (today - timedelta(days=30)).isoformat(),
                "to_date": today.isoformat(),
                "donations": ROW_COUNT,
                "inventory_units": ROW_COUNT,
                "donor_profiles": DONOR_COUNT,
            }
        ),
        encoding="utf-8",
    )
    try:
        credentials_path.chmod(0o600)
    except OSError:
        pass
    print(f"Seeded {ROW_COUNT} synthetic donation and inventory records across {DONOR_COUNT} donors.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials-file", required=True, type=Path)
    seed(parser.parse_args().credentials_file)
