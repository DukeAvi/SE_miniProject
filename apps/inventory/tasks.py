"""Scheduled inventory maintenance tasks."""

from datetime import date

from celery import shared_task

from .services import run_inventory_expiry_job


@shared_task(name="apps.inventory.tasks.expire_eligible_blood_units")
def expire_eligible_blood_units(as_of_date=None):
    """Expire eligible units; `as_of_date` is available for deterministic tests."""
    if isinstance(as_of_date, str):
        as_of_date = date.fromisoformat(as_of_date)
    run = run_inventory_expiry_job(as_of_date=as_of_date)
    return {
        "job_name": run.job_name,
        "run_date": run.run_date.isoformat(),
        "status": run.status,
        "processed_count": run.processed_count,
        "expired_count": run.expired_count,
        "attempt_count": run.attempt_count,
    }
