# Final unit and integration test report

Execution date: 2026-11-16. Tested source: `827819fa6b17d283c0886a5a71005935c3aaeddc` (final donor application plus QA-only fixture/connection corrections). Application source matches donor PR #186; subsequent documentation commits do not change that behavior.

Environment: Linux/WSL2, Python 3.13.5, Django 5.2.18, pytest 9.1.1, Coverage.py 7.17.3. Default suite: in-memory SQLite; concurrency checks: disposable PostgreSQL 16 sandbox on loopback, synthetic records only.

## Results

| Suite | Collected | Passed | Failed | SQLite skips |
| --- | ---: | ---: | ---: | ---: |
| Unit | 133 | 133 | 0 | 0 |
| Integration | 538 | 533 | 0 | 5 |
| Total | 671 | 666 | 0 | 5 |

The full suite under branch coverage completed in 68.29 seconds. All 666 executed cases passed. The five SQLite skips were separately executed on PostgreSQL and all five passed without the earlier worker-connection teardown warnings. These are complementary executions, not extra unique cases.

## PostgreSQL checks

Each case ran in a fresh pytest-created test database using `pytest --ds=bbms.settings -q <node-id>`. Temporary local credentials were supplied through the environment and are not committed. Worker connections are explicitly closed before pytest teardown.

| Case | Result |
| --- | --- |
| test_concurrent_duplicate_requests_create_at_most_one_active_appointment | 1 passed, 2.20s |
| test_concurrent_bookings_cannot_exceed_slot_capacity | 1 passed, 2.09s |
| test_concurrent_reservation_cannot_change_the_same_unit_twice | 1 passed, 2.22s |
| test_concurrent_requests_cannot_reserve_the_same_unit | 1 passed, 2.48s |
| test_concurrent_stock_reductions_create_one_crossing_alert | 1 passed, 2.62s |

The compatibility suite covers all 64 ABO/Rh pairings across four components. The permission suite checks 21 operations across four roles (84 cells). New donor onboarding tests cover Staff-only profile verification, bounded lookup, invalid input, duplicates, rollback and direct service authorization.

Sanitized measured counts are retained in [final-execution.json](../evidence/final-execution.json). Product code was not weakened to make tests pass.

## Historical evidence

The teammate's original preliminary report is preserved at [2026-11-15-unit-test-report.md](history/2026-11-15-unit-test-report.md). Historical failures, skips and measurements are not the current result.
