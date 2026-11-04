from django.core.management.base import BaseCommand, CommandError

from apps.audit.services import run_retention


class Command(BaseCommand):
    help = "Purge audit events older than the one-year retention period."

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Delete eligible records. Without this flag, report the eligible count only.",
        )

    def handle(self, *args, **options):
        try:
            result = run_retention(dry_run=not options["execute"])
        except Exception as exc:
            raise CommandError("Audit retention run failed.") from exc

        mode = "purged" if options["execute"] else "dry run"
        self.stdout.write(
            self.style.SUCCESS(
                f"Audit retention {mode}: run={result['run_id']} "
                f"cutoff={result['cutoff'].isoformat()} "
                f"eligible={result['eligible_count']} deleted={result['deleted_count']}"
            )
        )
