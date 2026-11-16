# Final code coverage report

Execution date: 2026-11-16. Tested source: `827819fa6b17d283c0886a5a71005935c3aaeddc` (final donor application plus QA-only fixture/connection corrections). Application source matches donor PR #186; subsequent documentation commits do not change that behavior.

Environment: Linux/WSL2, Python 3.13.5, Django 5.2.18, pytest 9.1.1, Coverage.py 7.17.3. Default suite: in-memory SQLite; concurrency checks: disposable PostgreSQL 16 sandbox on loopback, synthetic records only.

## Measurement

Scope: executable Python under `apps/`. Frontend JavaScript/TypeScript, operational scripts and the test suite itself are excluded from this Python measurement. No exclusion directives were configured; no new coverage threshold is invented.

| Metric | Covered | Total | Coverage |
| --- | ---: | ---: | ---: |
| Statements / executable lines | 3036 | 3297 | 92.08% |
| Branch outcomes | 532 | 646 | 82.35% |

Coverage.py's combined statement/branch figure is 90.49%; it is not the line-only percentage. The measurement run produced 666 passed and five SQLite skips in 68.29 seconds; all five skipped cases separately passed on PostgreSQL.

| Package | Statements | Statement coverage | Branches | Branch coverage |
| --- | ---: | ---: | ---: | ---: |
| accounts | 390/413 | 94.43% | 80/94 | 85.11% |
| adminops | 332/358 | 92.74% | 72/88 | 81.82% |
| audit | 252/258 | 97.67% | 36/38 | 94.74% |
| core | 344/357 | 96.36% | 86/98 | 87.76% |
| donors | 518/551 | 94.01% | 66/88 | 75.00% |
| inventory | 510/620 | 82.26% | 87/108 | 80.56% |
| notifications | 252/274 | 91.97% | 30/38 | 78.95% |
| requests | 438/466 | 93.99% | 75/94 | 79.79% |

## Reproduction

Run with the documented development dependencies and Coverage.py 7.17.3 available in the local QA environment:

```bash
python -m coverage run --branch --source=apps -m pytest -q
python -m coverage json -o /tmp/bbms-coverage.json
python -m coverage report
```

The verification run used the repository virtual environment and temporary Coverage.py installation, with `COVERAGE_FILE=/tmp/bbms-final.coverage`. Durable sanitized counts are committed in [final-execution.json](../evidence/final-execution.json). No database or credential is included.

## Historical evidence

The teammate's original preliminary report is preserved at [2026-11-15-coverage-report.md](history/2026-11-15-coverage-report.md). Historical failures, skips and measurements are not the current result.
