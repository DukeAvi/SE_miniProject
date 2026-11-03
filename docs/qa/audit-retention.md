# TC-Audit-02: one-year audit retention evidence

**Revision:** record the final PR head SHA here after the issue commit.
**Execution date:** 2026-11-04 Asia/Kolkata (automated checks below).
**Environment:** Python 3.14.6, Django 5.2.18, pytest 9.1.1, SQLite in-memory test database.
**Data:** generated synthetic audit rows only; no donor, recipient, clinical, or production data.

## Test objective and setup

Verify that the retention command uses a strict UTC one-year anniversary, does
not delete a row exactly at the cutoff, removes only older rows after explicit
execution, logs dry-run/success/failure runs, preserves search of retained rows,
and leaves ordinary model and queryset deletion blocked. Tests freeze the
application clock and create rows immediately before, exactly at, and after the
cutoff.

## Results

| Check | Expected | Observed |
|---|---|---|
| Row one microsecond before the one-year cutoff | Eligible; removed only with `--execute` | Pass |
| Row exactly at the cutoff | Retained | Pass |
| Row after the cutoff | Retained | Pass |
| Dry-run command | Count eligible rows, delete none, write dry-run audit event | Pass |
| Successful purge | Delete eligible rows and write success event atomically | Pass |
| Simulated delete failure | Roll back deletion and write failure event | Pass |
| Ordinary instance/queryset delete | Rejected | Pass |
| Retained-row search and index dimensions | Search returns retained rows; expected time/actor/action/entity indexes exist | Pass |
| Naive timestamps / leap-day anniversary | Reject naive time; clamp Feb 29 anniversary to Feb 28 | Pass |

## Commands and observed output

```text
DJANGO_SETTINGS_MODULE=bbms.settings_test /tmp/bbms-sprint2-venv/bin/pytest tests/integration/audit -q
67 passed in 9.26s

DJANGO_SETTINGS_MODULE=bbms.settings_test /tmp/bbms-sprint2-venv/bin/python manage.py check
System check identified no issues (0 silenced).

DJANGO_SETTINGS_MODULE=bbms.settings_test /tmp/bbms-sprint2-venv/bin/python manage.py makemigrations --check --dry-run
No changes detected

DJANGO_SETTINGS_MODULE=bbms.settings_test /tmp/bbms-sprint2-venv/bin/python manage.py migrate --noinput
All migrations applied successfully, including audit.0006.

/tmp/bbms-sprint2-venv/bin/ruff check apps/audit tests/integration/audit
All checks passed!

DJANGO_SETTINGS_MODULE=bbms.settings_test /tmp/bbms-sprint2-venv/bin/pytest -q
650 passed, 5 skipped in 146.35s

git diff --check
Passed (no whitespace errors).
```

The five full-suite skips cover PostgreSQL row-lock/concurrency behavior, which
SQLite does not provide. The retention-specific checks ran on SQLite. A
PostgreSQL CI run remains necessary before merge.
