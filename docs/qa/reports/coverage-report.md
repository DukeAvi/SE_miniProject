# Code Coverage Report — Sprint 2 QA

**Revision:** `f693371ba0fce6d5d7d57e03ff2aa6dfff47d8f2` (`main`)
**Date:** 2026-11-05 (Asia/Kolkata)
**Scope:** Python application package `apps/`; frontend JavaScript/TypeScript is excluded.
**Tool:** Coverage.py 7.17.2 with branch measurement; pytest ran on the SQLite test backend.

## Results

| Measure | Covered | Total | Coverage |
| --- | ---: | ---: | ---: |
| Executable statements / lines | 2,864 | 3,119 | 90.32% |
| Branches | 513 | 620 | 82.74% |

The run produced 639 passed, 1 failed, and 5 skipped tests. Coverage includes the executed paths from that run, including the failing test up to its assertion. The result is a repository-wide Python baseline, not proof that each requirement is covered or that unexecuted branches are safe.

## Reproduction

```text
COVERAGE_FILE=/tmp/bbms-main-qa.coverage /tmp/bbms-sprint2-venv/bin/python -m coverage run --branch --source=apps -m pytest -q
COVERAGE_FILE=/tmp/bbms-main-qa.coverage /tmp/bbms-sprint2-venv/bin/python -m coverage report --data-file=/tmp/bbms-main-qa.coverage
```

The raw data and JSON summary were kept in `/tmp` and are not committed; the percentages above are copied from Coverage.py's generated total (`2864/3119` statements and `513/620` branches). No external coverage threshold was specified in the SRS, STP, or repository CI.
