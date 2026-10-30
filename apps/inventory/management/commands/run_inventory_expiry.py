"""Test-only manual expiry trigger."""

from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.inventory.services import InventoryExpiryJobFailed, run_inventory_expiry_job


class Command(BaseCommand):
    help = "Manually run inventory expiry for a test date (DEBUG only)."

    def add_arguments(self, parser):
        parser.add_argument("--as-of-date", required=True, type=date.fromisoformat)

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Manual expiry is available only when DEBUG=True.")
        try:
            run = run_inventory_expiry_job(as_of_date=options["as_of_date"])
        except InventoryExpiryJobFailed as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(
            self.style.SUCCESS(
                f"{run.status}: processed={run.processed_count} expired={run.expired_count}"
            )
        )
