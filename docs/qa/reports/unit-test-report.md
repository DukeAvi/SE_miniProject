# Unit Test Report — Issue #183 baseline

**Status:** Preliminary baseline; final execution is pending merge of issue #182.

## Revision and environment

- Repository: `DukeAvi/SE_miniProject`
- Tested code revision: `12b8e60` (`test/183-final-qa-reports`); application source remains at synchronized `origin/main` revision `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`. The difference is limited to the two QA test-fixture/assertion corrections described below.
- Execution date: 2026-11-15 (Asia/Calcutta)
- Local environment: Windows x64, Python 3.12.7, Django 5.2.18, pytest 9.1.1, psycopg 3.3.6, SQLite in-memory for the default suite
- PostgreSQL sandbox: PostgreSQL 16.16, loopback-only disposable cluster, port 55432, trust authentication, database `postgres`; pytest created its disposable test database. No shared or production database was used.

## Full backend suite

Command: `python -m pytest -q`

Result: **650 passed, 0 failed, 5 skipped** in 54.36 seconds. Exit code 0. The executed-test pass rate is 650/650 (100%); among all 655 collected cases, 650/655 passed (99.24%). The five PostgreSQL-only cases are separately executed below; their SQLite skips are not counted as passes.

Historical CI failures on report-only commits `5fbf613`, `41c9b62`, and `6e3c1bb` all failed on `test_raising_threshold_can_trigger_alert_and_lowering_it_can_clear_active_state`. The test froze `apps.inventory.services.blood_bank_today`, but the admin endpoint calls the separately imported alias in `apps.adminops.views`; that alias used the actual date (2026-11-15), so test units expiring 2026-11-10 were considered expired and the alert correctly stayed active. The test fixture now freezes the view alias too. This corrected test determinism; application behavior was not changed.

All three cited CI runs (`43736538474`, `43736855078`, `43737103165`) reproduce the same stale-date test-fixture failure on report-only commits; the pytest suite had 649 passed, 1 failed, and 5 skipped each time. The report-only diffs did not change executable code. The fixture correction is in `12b8e60`; the new CI run for that head is pending. Ruff, Django checks, migration checks, and migration application passed on the earlier runs. CI uses SQLite settings, so PostgreSQL-only cases are skipped there.

The five skips explicitly require PostgreSQL row-lock/concurrency semantics and are not counted as passing tests. Their PostgreSQL results are recorded below and in the [execution summary](QA-002-execution-summary.md).

## PostgreSQL concurrency cases

Each PostgreSQL case was run in a separate pytest process with a fresh test database. Running all five in one process was also tried first; because these cases use `transaction=True`, pytest flushes migration-seeded threshold rows between cases. That combined invocation produced misleading missing-threshold errors for later cases and is retained only as diagnostic history, not as the reported final result.

```powershell
$env:DJANGO_SECRET_KEY='(temporary test-only value)'; $env:DJANGO_DEBUG='true'; $env:POSTGRES_DB='postgres'; $env:POSTGRES_USER='bbms_qa183'; $env:POSTGRES_PASSWORD=''; $env:POSTGRES_HOST='127.0.0.1'; $env:POSTGRES_PORT='55432'; $env:POSTGRES_SSLMODE='disable'
python -m pytest --ds=bbms.settings -q tests/integration/donors/test_appointment_booking.py::test_concurrent_duplicate_requests_create_at_most_one_active_appointment
python -m pytest --ds=bbms.settings -q tests/integration/donors/test_appointment_booking.py::test_concurrent_bookings_cannot_exceed_slot_capacity
python -m pytest --ds=bbms.settings -q tests/integration/inventory/test_stock_transitions.py::test_concurrent_reservation_cannot_change_the_same_unit_twice
python -m pytest --ds=bbms.settings -q tests/integration/requests/test_fulfillment.py::test_concurrent_requests_cannot_reserve_the_same_unit
python -m pytest --ds=bbms.settings -q tests/integration/inventory/test_low_stock_alerts.py::test_concurrent_stock_reductions_create_one_crossing_alert
```

Test-only secret values are not recorded. PostgreSQL ran locally in a disposable cluster. Each case reported **1 passed** when run independently on PostgreSQL 16.16. Exact expected and actual behavior:

| Test case | Purpose and expected result | Actual result |
|---|---|---|
| `test_concurrent_duplicate_requests_create_at_most_one_active_appointment` | Concurrent duplicate booking request should create at most one active appointment. | Pass; both workers and invariant assertions executed. |
| `test_concurrent_bookings_cannot_exceed_slot_capacity` | Concurrent bookings must not exceed configured slot capacity. | Pass; both workers and capacity assertions executed. |
| `test_concurrent_reservation_cannot_change_the_same_unit_twice` | Concurrent attempts to reserve one unit permit one transition and reject the competing transition; emit one reservation audit event. | Pass after the test supplied its frozen business date and scoped the audit assertion to `UNIT_RESERVED`; competing low-stock audit events are correctly outside that assertion. |
| `test_concurrent_requests_cannot_reserve_the_same_unit` | Two requests racing for one unit yield one successful reservation and one conflict. | Pass; one reservation succeeded and the competing request conflicted. |
| `test_concurrent_stock_reductions_create_one_crossing_alert` | Concurrent stock reductions crossing the threshold create one alert, audit event and notification. | Pass; one crossing alert and associated records were asserted. |

PostgreSQL configuration for all five: server 16.16, database `postgres` with pytest-created test database, user `bbms_qa183`, host `127.0.0.1`, port `55432`, SSL mode `disable`, local trust authentication. The test server was bound to loopback only. The exact invocation and temporary environment setup are above.

Pytest emitted a teardown warning because three worker connections were still active when it attempted to remove its `test_postgres` database. The cluster was a newly created disposable test cluster; it was stopped after execution, which closed those connections. No pre-existing database was targeted.

The final independent runs also emitted pytest teardown warnings because two worker connections remained active at teardown. Before each next case, only the temporary `test_postgres` database in this disposable cluster was dropped with `WITH (FORCE)`; the server was stopped after test execution. There were no retries; each final case ran once and passed.

The fifth case also passed in PostgreSQL CI on application baseline `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`, job “Verify low-stock crossing locks on PostgreSQL” in [GitHub Actions run 42607673691](https://github.com/DukeAvi/SE_miniProject/actions/runs/42607673691). The local isolated result now independently passes as well.

## Historical results

Earlier reports for `f693371` and `fd0e96f` remain historical and are not evidence for this revision. The known report fixture defect #174 was corrected by merged PR #178. The three CI failures described above are test-fixture issues corrected in `12b8e60`; no application defect was demonstrated by them.
