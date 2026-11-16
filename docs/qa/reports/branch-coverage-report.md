# Final branch coverage report

Execution date: 2026-11-16. Tested source: `827819fa6b17d283c0886a5a71005935c3aaeddc` (final donor application plus QA-only fixture/connection corrections). Application source matches donor PR #186; subsequent documentation commits do not change that behavior.

Environment: Linux/WSL2, Python 3.13.5, Django 5.2.18, pytest 9.1.1, Coverage.py 7.17.3. Default suite: in-memory SQLite; concurrency checks: disposable PostgreSQL 16 sandbox on loopback, synthetic records only.

Coverage.py 7.17.3 measured **532/646 branch outcomes (82.35%)**, with 114 missing outcomes and 94 partial branches. No branch exclusions were configured.

The measured scope is Python `apps/`; this is not frontend branch coverage. The run completed with 666 passed and five SQLite-only skips. The concurrency cases separately passed on PostgreSQL; those separate processes are not included in the SQLite coverage percentage.

Reproduction and per-package counts are in the [code coverage report](coverage-report.md); durable totals are in [final-execution.json](../evidence/final-execution.json). Coverage identifies unexecuted paths; it is not a guarantee that every possible input or production condition is safe.

## Historical evidence

The teammate's original preliminary report is preserved at [2026-11-15-branch-coverage-report.md](history/2026-11-15-branch-coverage-report.md). Historical failures, skips and measurements are not the current result.
