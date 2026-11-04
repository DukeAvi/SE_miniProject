# Unit Test Report — Sprint 2 QA

**Revision:** `f693371ba0fce6d5d7d57e03ff2aa6dfff47d8f2` (`main`)
**Date:** 2026-11-05 (Asia/Kolkata)
**Runner:** Python 3.14.6, pytest 9.1.1, Django 5.2.18, SQLite test database.

## Results

| Suite | Collected | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: |
| `tests/unit` | 133 | 133 | 0 | 0 |
| `tests/integration` | 512 | 506 | 1 | 5 |
| Total | 645 | 639 | 1 | 5 |

The single failure is documented in [QA-002 execution summary](QA-002-execution-summary.md) and tracked as [#174](https://github.com/DukeAvi/SE_miniProject/issues/174). Five integration checks that require PostgreSQL locking/concurrency were skipped by the SQLite test backend; PostgreSQL CI/runtime execution is required to close that gap.

## Focused evidence

- Role-policy matrix: 21 protected operations × four roles (84 cells), including deny-by-default and denial audit behavior — pass.
- Blood compatibility: 64 ABO/Rh combinations × four components — pass.
- Donor eligibility, booking, donation recording, inventory creation/search/transitions/expiry, request submission/decisions/fulfillment/history, notification delivery, audit, and admin operations — automated tests ran within the full suite; see the named test modules under `tests/unit/` and `tests/integration/`.
- Operational reports: the full suite exposed a date-dependent inventory-summary fixture failure; it remains open.

This report does not claim UAT, performance/load, uptime, full browser accessibility, or production database concurrency verification.
