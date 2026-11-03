"""Check notification outbox backlog and recent delivery failure thresholds."""

import json

from django.core.management.base import BaseCommand, CommandError

from apps.notifications.monitoring import notification_delivery_health


class Command(BaseCommand):
    help = "Exit nonzero when notification backlog or delivery failure rate is high."

    def handle(self, *args, **options):
        healthy, metrics = notification_delivery_health()
        output = json.dumps(metrics, sort_keys=True)
        if not healthy:
            self.stderr.write(self.style.ERROR(output))
            raise CommandError("Notification delivery health check failed.")
        self.stdout.write(self.style.SUCCESS(output))
