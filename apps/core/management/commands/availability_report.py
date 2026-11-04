import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from django.core.management.base import BaseCommand, CommandError

from apps.core.availability import calculate_availability, parse_prometheus_samples


class Command(BaseCommand):
    help = "Report monthly health-probe availability excluding planned maintenance."

    def add_arguments(self, parser):
        parser.add_argument("--month", required=True, help="Month in YYYY-MM format")
        parser.add_argument("--prometheus-url", default="http://localhost:9090")
        parser.add_argument("--maintenance-file", default="deployment/maintenance.json")

    def handle(self, *args, **options):
        try:
            start = datetime.strptime(options["month"], "%Y-%m").replace(tzinfo=UTC)
            end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            maintenance = json.loads(Path(options["maintenance_file"]).read_text())
            windows = [
                (datetime.fromisoformat(item["start"].replace("Z", "+00:00")),
                 datetime.fromisoformat(item["end"].replace("Z", "+00:00")))
                for item in maintenance.get("windows", [])
            ]
            query = urlencode({
                "query": 'probe_success{job="bbms-health"}',
                "start": start.isoformat(),
                "end": end.isoformat(),
                "step": "60s",
            })
            with urlopen(f"{options['prometheus_url'].rstrip('/')}/api/v1/query_range?{query}", timeout=10) as response:
                payload = json.load(response)
            results = payload["data"]["result"]
            if not results:
                raise CommandError("No health-probe samples exist for the requested month.")
            report = calculate_availability(parse_prometheus_samples(results[0]["values"]), windows)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise CommandError("Availability data could not be read.") from exc
        report["month"] = options["month"]
        self.stdout.write(json.dumps(report, sort_keys=True))
