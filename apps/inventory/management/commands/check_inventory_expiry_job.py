"""Health command for a process monitor to detect failed or missing runs."""

from django.core.management.base import BaseCommand, CommandError

from apps.inventory.monitoring import inventory_expiry_job_health


class Command(BaseCommand):
    help = "Exit nonzero if inventory expiry failed or has not succeeded recently."

    def handle(self, *args, **options):
        healthy, message = inventory_expiry_job_health()
        if not healthy:
            self.stderr.write(self.style.ERROR(message))
            raise CommandError("Inventory expiry job health check failed.")
        self.stdout.write(self.style.SUCCESS(message))
