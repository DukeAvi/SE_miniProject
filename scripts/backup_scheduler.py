"""Run daily backups and an independent five-minute freshness watchdog."""

from datetime import UTC, datetime, time, timedelta
import os
import sys
import time as sleep_time

from scripts.db_backup import backup, check_freshness, latest_backup, validate_configuration


RETRY_SECONDS = 15 * 60
FRESHNESS_INTERVAL_SECONDS = 5 * 60


def next_backup_time(now: datetime, latest_success_at: datetime | None = None) -> datetime:
    today = datetime.combine(now.date(), time(hour=2), tzinfo=UTC)
    if now < today:
        return today
    if latest_success_at is not None and latest_success_at.astimezone(UTC).date() == now.date():
        return today + timedelta(days=1)
    return now


def run_scheduler(*, mode: str | None = None, clock=None, sleep=None, run_backup=None, check=None):
    mode = mode or os.environ.get("BACKUP_SCHEDULER_MODE", "worker")
    if mode not in {"worker", "watchdog"}:
        raise ValueError("BACKUP_SCHEDULER_MODE must be worker or watchdog")
    validate_configuration(mode=mode)
    clock = clock or (lambda: datetime.now(UTC))
    sleep = sleep or sleep_time.sleep
    run_backup = run_backup or backup
    check = check or check_freshness
    now = clock()
    latest_success_at = None
    state_check_failed = False
    if mode == "worker" and now >= datetime.combine(now.date(), time(hour=2), tzinfo=UTC):
        try:
            latest = latest_backup()
            latest_success_at = latest["LastModified"] if latest else None
        except Exception:
            print("could not inspect backup state; retrying in 15 minutes", file=sys.stderr, flush=True)
            state_check_failed = True
    next_backup = (
        now + timedelta(seconds=RETRY_SECONDS)
        if state_check_failed
        else next_backup_time(now, latest_success_at)
    )
    last_successful_backup_date = (
        latest_success_at.astimezone(UTC).date()
        if latest_success_at and latest_success_at.astimezone(UTC).date() == now.date()
        else None
    )
    next_check = now
    while True:
        now = clock()
        if mode == "worker" and now >= next_backup and last_successful_backup_date != now.date():
            try:
                object_key = run_backup(now=now)
                last_successful_backup_date = now.date()
                print(f"verified backup created: {object_key}", flush=True)
                next_backup = next_backup_time(now + timedelta(seconds=1), now)
            except Exception:
                print("scheduled backup failed; retrying in 15 minutes", file=sys.stderr, flush=True)
                next_backup = now + timedelta(seconds=RETRY_SECONDS)
        if now >= next_check:
            try:
                check(now=now)
            except Exception:
                print("backup freshness check or alert delivery failed", file=sys.stderr, flush=True)
            next_check = now + timedelta(seconds=FRESHNESS_INTERVAL_SECONDS)
        wake_at = next_check
        if mode == "worker" and last_successful_backup_date != now.date():
            wake_at = min(wake_at, next_backup)
        sleep(max(0, (wake_at - clock()).total_seconds()))


if __name__ == "__main__":
    try:
        run_scheduler()
    except KeyboardInterrupt:
        raise SystemExit(0)
    except ValueError:
        print("backup scheduler configuration is invalid", file=sys.stderr, flush=True)
        raise SystemExit(2)
