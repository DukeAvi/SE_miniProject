# Final Unit and Integration Test Report

## Purpose and tested revision

This report records final BBMS backend verification. It covers the unit and integration suites listed below, including the PostgreSQL concurrency cases.

- **Execution date:** 2026-11-16
- **Tested revision:** `827819fa6b17d283c0886a5a71005935c3aaeddc`
- **Application revision represented:** `daa75f5864ab9e56b53b8c3c735f14c53c349681` (merged PR #186)
- **Environment:** Linux/WSL2; Python 3.13.5; Django 5.2.18; pytest 9.1.1; Coverage.py 7.17.3
- **Data:** disposable, synthetic test records only

The later documentation revisions do not change `apps/`, `bbms/`, `frontend/`, or `tests`; this remains the final execution evidence for the application snapshot.

## Overall result

| Execution | Collected | Passed | Failed | Skipped | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| SQLite unit and integration suite | 671 | 666 | 0 | 5 | Pass within SQLite capability |
| PostgreSQL concurrency rerun | 5 | 5 | 0 | 0 | Pass |
| Unique planned automated cases | 671 | 671 | 0 | 0 | Pass |

The SQLite coverage run completed in **68.29 seconds**. Its five skipped tests require PostgreSQL row locks. Each was then run in a fresh disposable PostgreSQL test database, with worker connections closed before teardown; all five passed with no teardown warnings.

## Suite composition

| Level | Test files | Collected cases | Purpose |
| --- | ---: | ---: | --- |
| Unit | 18 | 133 | Pure rules, policy, validation, configuration, adapters, logging, backup and security behavior |
| Integration | 26 | 538 | API endpoints, services, transactions, migrations, role ownership, jobs and browser-facing workflows |
| Total | 44 | 671 | Regression suite for all implemented requirements |

## Coverage by application area

| Area | Test files | Behaviour verified |
| --- | ---: | --- |
| Accounts and profiles | 4 integration files | Registration, password protection, login/logout, session expiry, CSRF, throttling, profile ownership and writable-field restrictions |
| Donors and donations | 3 integration + 1 unit file | Eligibility boundaries, slot capacity, duplicate prevention, cancellation, immutable donation recording, history, Staff donor lookup and verified-profile onboarding |
| Inventory | 6 integration files | Unit creation and validation, search/privacy, state transitions, ledger/audit rollback, expiry jobs, low-stock alerts and hostile-input validation |
| Requests and compatibility | 4 integration + 1 unit file | Request submission, decisions, recipient ownership/history, FEFO reservation, issue idempotency and the component-aware compatibility matrix |
| Notifications | 1 integration + 1 unit file | Outbox creation, retries, failure handling, ownership and console/mock adapters |
| Administration and audit | 5 integration files | Staff account management, reports, append-only audit search, retention/purge and security-event recording |
| Core, deployment and operations | 14 unit/integration files | Permission matrix, availability, metrics, health checks, monitoring, TLS configuration, backups, compression and operational defaults |

The suite includes the **84-cell role policy matrix** (21 protected operations across Donor, Recipient, Staff and Admin) and the **256-cell compatibility matrix** (eight donor groups by eight recipient groups across four components).

## PostgreSQL-only concurrency checks

| Test | What it proves | Result |
| --- | --- | --- |
| `test_concurrent_duplicate_requests_create_at_most_one_active_appointment` | One donor cannot gain two active appointments for the same slot | 1 passed, 2.20s |
| `test_concurrent_bookings_cannot_exceed_slot_capacity` | Competing bookings cannot exceed slot capacity | 1 passed, 2.09s |
| `test_concurrent_reservation_cannot_change_the_same_unit_twice` | A unit cannot be reserved twice under competing transactions | 1 passed, 2.22s |
| `test_concurrent_requests_cannot_reserve_the_same_unit` | Concurrent requests cannot allocate the same inventory unit | 1 passed, 2.48s |
| `test_concurrent_stock_reductions_create_one_crossing_alert` | A threshold crossing creates one low-stock alert | 1 passed, 2.62s |

## Requirement and role coverage

- The [RTM](RTM-execution.md) maps all 34 functional, non-functional and security requirement IDs to their design and test identifiers.
- The final browser walkthrough exercises new donor registration, Staff verification, booking/cancellation, donation and unit creation, request submission and fulfillment, and Admin Staff-account creation. See [TC-UX-01](../TC-UX-01.md).
- Unit/integration tests cover success, validation, authorization, ownership, rollback, idempotency, append-only records, exact date boundaries, and documented error cases where the implemented requirement calls for them.

## Reproduction and evidence

The recorded coverage execution used the following command pattern with an isolated SQLite test database:

```bash
python -m coverage run --branch --source=apps -m pytest -q
python -m coverage json -o /tmp/bbms-coverage.json
python -m coverage report
```

The PostgreSQL cases were run individually with `pytest --ds=bbms.settings -q <node-id>` against a disposable local PostgreSQL 16 database. Sanitized aggregate counts and package coverage are retained in [final-execution.json](../evidence/final-execution.json); code coverage details are in the [coverage report](coverage-report.md).

## Evidence files

- [Final execution result](../evidence/final-execution.json)
- [Release readiness record](../release-readiness.md)
- [Requirement traceability matrix](RTM-execution.md)
