"""Capture sanitized PostgreSQL query plans used by the performance profile."""

import json
import os
from pathlib import Path
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bbms.settings")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main(output: Path) -> None:
    import django

    django.setup()

    from django.utils import timezone

    from apps.donors.models import Donation
    from apps.inventory.models import BloodUnit

    today = timezone.localdate()
    start = today.replace(day=1)
    inventory_plan = BloodUnit.objects.filter(
        status=BloodUnit.Status.AVAILABLE,
        blood_group="O+",
        component=BloodUnit.Component.RBC,
        expiry_date__gt=today,
    ).order_by("expiry_date", "created_at", "id")[:100].explain(
        analyze=True,
        buffers=True,
        format="json",
    )
    report_plan = Donation.objects.filter(
        donation_date__gte=start,
        donation_date__lte=today,
    ).order_by("donation_date", "pk")[:100].explain(
        analyze=True,
        buffers=True,
        format="json",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "generated_on": today.isoformat(),
                "inventory_search": json.loads(inventory_plan),
                "dashboard_donation_report": json.loads(report_plan),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main(Path(os.environ.get("PERF_QUERY_PLAN_FILE", "performance-results/query-plans.json")))
