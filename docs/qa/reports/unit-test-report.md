# Unit Test Report — Issue #183 baseline

**Status:** Preliminary baseline; final execution is pending merge of issue #182.

## Revision and environment

- Repository: `DukeAvi/SE_miniProject`
- Tested application revision: `f913fa70a5c6e3b50e07c7f00fc579928508c0ba` (`origin/main` on 2026-11-15)
- Execution date: 2026-11-15 (Asia/Calcutta)
- Local environment: Windows x64, Python 3.12.7, Django 5.2.18, pytest 9.1.1, psycopg 3.3.6, SQLite in-memory for the default suite
- PostgreSQL sandbox: PostgreSQL 16.16, loopback-only disposable cluster, port 55432, trust authentication, database `postgres`; pytest created its disposable test database. No shared or production database was used.

## Full backend suite

Command: `python -m pytest -q`

Result: **649 passed, 1 failed, 5 skipped** in 54.15 seconds. Exit code 1. The executed-test pass rate is 649/650 (99.85%); among all 655 collected cases, 649/655 passed (99.08%).

The failure is `tests/integration/inventory/test_low_stock_alerts.py::test_raising_threshold_can_trigger_alert_and_lowering_it_can_clear_active_state`: after lowering the threshold from 5 to 4 with four available units, `alert_active` remains true. The failure is a real failing assertion on this baseline, not an environment skip. No application or test code was changed as part of this report task.

The five skips explicitly require PostgreSQL row-lock/concurrency semantics and are not counted as passing tests. Their PostgreSQL results are recorded below and in the [execution summary](QA-002-execution-summary.md).

## PostgreSQL concurrency cases

The command set all five node IDs in one pytest invocation:

```powershell
$env:DJANGO_SECRET_KEY='(temporary test-only value)'; $env:DJANGO_DEBUG='true'; $env:POSTGRES_DB='postgres'; $env:POSTGRES_USER='bbms_qa183'; $env:POSTGRES_PASSWORD=''; $env:POSTGRES_HOST='127.0.0.1'; $env:POSTGRES_PORT='55432'; $env:POSTGRES_SSLMODE='disable'
python -m pytest --ds=bbms.settings -q `
  tests/integration/donors/test_appointment_booking.py::test_concurrent_duplicate_requests_create_at_most_one_active_appointment `
  tests/integration/donors/test_appointment_booking.py::test_concurrent_bookings_cannot_exceed_slot_capacity `
  tests/integration/inventory/test_stock_transitions.py::test_concurrent_reservation_cannot_change_the_same_unit_twice `
  tests/integration/requests/test_fulfillment.py::test_concurrent_requests_cannot_reserve_the_same_unit `
  tests/integration/inventory/test_low_stock_alerts.py::test_concurrent_stock_reductions_create_one_crossing_alert
```

Test-only secret values are not recorded. PostgreSQL ran on the same machine with a disposable local cluster. Result: **2 passed, 3 failed**, 11.38 seconds. The duplicate active appointment and slot-capacity cases passed. The inventory transition case returned two conflicts where the test expects one success and one conflict. The request reservation case errored because `StockThreshold` was absent when threshold evaluation ran. The low-stock crossing case failed before starting worker threads because its expected `StockThreshold` row was absent. These are failures, not skips. They require application-owner investigation; this reporting task does not alter product or test code.

| Test case | Purpose and expected result | Actual result |
|---|---|---|
| `test_concurrent_duplicate_requests_create_at_most_one_active_appointment` | Concurrent duplicate booking request should create at most one active appointment. | Pass; PostgreSQL executed both workers and invariant assertions. |
| `test_concurrent_bookings_cannot_exceed_slot_capacity` | Concurrent bookings must not exceed the configured slot capacity. | Pass; PostgreSQL executed both workers and capacity assertions. |
| `test_concurrent_reservation_cannot_change_the_same_unit_twice` | Concurrent attempts to reserve the same unit should permit one transition and reject the competing transition. | Fail; both workers returned `conflict`, while the test expected one `ok` and one `conflict`. |
| `test_concurrent_requests_cannot_reserve_the_same_unit` | Two requests racing for one unit should yield one successful reservation and one conflict. | Fail/error; service threshold evaluation raised `StockThreshold.DoesNotExist` before the expected `[200, 409]` statuses could be asserted. |
| `test_concurrent_stock_reductions_create_one_crossing_alert` | Concurrent stock reductions crossing the threshold should create one alert, audit event and notification. | Fail before concurrency; test setup could not retrieve its expected O+/RBC `StockThreshold` row. The same test passed in main CI on this revision, as separately linked below. |

PostgreSQL configuration for all five: server 16.16, database `postgres` with pytest-created test database, user `bbms_qa183`, host `127.0.0.1`, port `55432`, SSL mode `disable`, local trust authentication. The test server was bound to loopback only. The exact invocation and temporary environment setup are above.

Pytest emitted a teardown warning because three worker connections were still active when it attempted to remove its `test_postgres` database. The cluster was a newly created disposable test cluster; it was stopped after execution, which closed those connections. No pre-existing database was targeted.

The fifth case also passed in PostgreSQL CI on baseline `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`, job “Verify low-stock crossing locks on PostgreSQL” in [GitHub Actions run 42607673691](https://github.com/DukeAvi/SE_miniProject/actions/runs/42607673691). That CI result does not override the separate local fixture failure above.

## Historical results

Earlier reports for `f693371` and `fd0e96f` remain historical and are not evidence for this revision. The known report fixture defect #174 was corrected by merged PR #178; the failure on this current run is a different low-stock alert assertion.
