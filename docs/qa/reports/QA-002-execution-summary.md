# Final QA execution summary

Execution date: 2026-11-16. Tested source: `827819fa6b17d283c0886a5a71005935c3aaeddc` (final donor application plus QA-only fixture/connection corrections). Application source matches donor PR #186; subsequent documentation commits do not change that behavior.

Environment: Linux/WSL2, Python 3.13.5, Django 5.2.18, pytest 9.1.1, Coverage.py 7.17.3. Default suite: in-memory SQLite; concurrency checks: disposable PostgreSQL 16 sandbox on loopback, synthetic records only.

## Execution and coverage

- Collected: 671 cases (133 unit, 538 integration).
- SQLite run: 666 passed, zero failed, five PostgreSQL-only skips, 68.29 seconds under coverage.
- PostgreSQL: all five skipped concurrency cases passed independently with clean test-database teardown.
- Unique planned automated cases exercised across these runs: 671/671. SQLite skips are not counted as SQLite passes or counted twice.
- Statements: 3036/3297 (92.08%). Branches: 532/646 (82.35%). Python `apps/` scope only.
- Full compatibility and role-policy matrices passed. Actual donor, Staff, Recipient and Admin browser workflows passed; see the system and UX reports.

## Defects, history and disposition

#174 was resolved by PR #178. Later date/audit fixture assumptions were corrected by the QA contributor; the donor-profile audit catalogue assertion and service-level authorization were corrected during final review. Original failed outcomes remain in the [historical reports](history/). No unresolved automated failure is hidden by a skipped test or changed product rule.

The final observed automated failure count is zero. A product defect-density denominator was not agreed, so test-case failure rate is reported instead of inventing a density metric. Test-fixture and integration corrections were resolved before this report; their issue/PR timestamps retain the actual history. A separate daily defect-aging series was not collected.

## Evidence and release recommendation

- [Unit/integration and PostgreSQL results](unit-test-report.md)
- [System validation](system-validation-report.md)
- [Statement coverage](coverage-report.md) and [branch coverage](branch-coverage-report.md)
- [Durable measured summary](../evidence/final-execution.json)
- [Authoritative RTM](RTM-execution.md), [Test Plan](../test-plan.md), [release disposition](../release-readiness.md)

Recommend the classroom handoff with the already documented owner exceptions. Human UAT/screen-reader acceptance, complete-month availability and production-specific verification are not converted to passes. Original source requirement targets remain visible, and an owner exception is not evaluator approval.

The final release audit adds three separately verified planning-audit unit cases outside the measured Python application scope; its CI result is linked in the release record. These do not alter the measured application counts above.

## Historical evidence

The teammate's original preliminary report is preserved at [2026-11-15-QA-002-execution-summary.md](history/2026-11-15-QA-002-execution-summary.md). Historical failures, skips and measurements are not the current result.
