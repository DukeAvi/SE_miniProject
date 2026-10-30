"""Health check for expiry-run monitoring systems."""

from datetime import timedelta

from django.utils import timezone

from .models import InventoryJobRun
from .services import EXPIRY_JOB_NAME


MAX_EXPIRY_RUN_AGE = timedelta(hours=26)


def inventory_expiry_job_health(*, now=None):
    """Return a sanitized health result for an external monitor to poll."""
    now = now or timezone.now()
    latest = InventoryJobRun.objects.filter(job_name=EXPIRY_JOB_NAME).first()
    if latest is None:
        return False, "No inventory expiry run has been recorded."
    if latest.status == InventoryJobRun.Status.FAILED:
        return False, "The latest inventory expiry run failed."
    if latest.status == InventoryJobRun.Status.RUNNING and now - latest.started_at > MAX_EXPIRY_RUN_AGE:
        return False, "The latest inventory expiry run has been running too long."

    successful = InventoryJobRun.objects.filter(
        job_name=EXPIRY_JOB_NAME,
        status=InventoryJobRun.Status.SUCCEEDED,
    ).first()
    if successful is None or successful.finished_at is None:
        return False, "No successful inventory expiry run has been recorded."
    if now - successful.finished_at > MAX_EXPIRY_RUN_AGE:
        return False, "No successful inventory expiry run has completed within 26 hours."
    return True, "Inventory expiry job is healthy."
