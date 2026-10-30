# Inventory expiry job operations

The inventory expiry task implements BBMS-F-024 / DS-024 and TC-Inv-05. Celery Beat schedules it daily at 00:05 in `BLOOD_BANK_TIME_ZONE` (default `Asia/Kolkata`). The worker expires AVAILABLE and RESERVED units whose expiry date is today or earlier. Availability reads independently exclude units from the start of the expiry date, so correctness does not depend on the scheduled task having run.

## Runtime

Start Redis at the configured `CELERY_BROKER_URL` (default `redis://localhost:6379/0`), then run one Celery worker and one Beat scheduler:

```text
celery -A bbms worker --loglevel=INFO
celery -A bbms beat --loglevel=INFO
```

`INVENTORY_EXPIRY_BATCH_SIZE` controls the committed batch size (default 100). Every unit status update, inventory transaction, and audit event is atomic. Each batch commits independently. If a later batch fails, the JobRun is marked FAILED, earlier batches remain committed, and a retry safely processes the remaining eligible units.

## Monitoring and recovery

Configure the deployment's independent process monitor to run this command at least every 15 minutes:

```text
python manage.py check_inventory_expiry_job
```

It exits nonzero if the latest run failed, no successful run exists, or the last successful run is older than 26 hours. The command emits sanitized status text and can be connected to the deployment's alert channel. This monitor must run independently of Celery Beat so it can detect a stopped scheduler.

After confirming no expiry worker is still processing the run, a scheduled task can be retried for the same local date:

```text
celery -A bbms call apps.inventory.tasks.expire_eligible_blood_units --args='["YYYY-MM-DD"]'
```

The unique `(job_name, run_date)` row prevents overlapping invocations. Successful runs are no-ops when repeated; FAILED runs resume from the remaining eligible units. JobRun stores attempt counts, processed and expired counts, status, and a sanitized error description.

## Test-only manual trigger

The management command is available only with `DEBUG=True` and is intended for local test data:

```text
python manage.py run_inventory_expiry --as-of-date 2026-10-30
```

Never enable `DEBUG` in production to use this trigger. Production recovery uses the Celery task call above.
