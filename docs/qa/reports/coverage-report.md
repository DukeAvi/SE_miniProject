# Code Coverage Report — Issue #183 baseline

**Status:** Fresh baseline measurement; evaluation-final coverage is pending merge of #182.

## Revision and environment

- Tested code revision: `12b8e60` (test fixtures/assertions only); application source baseline: `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`
- Execution date: 2026-11-15 (Asia/Calcutta)
- Environment: Windows x64, Python 3.12.7, Django 5.2.18, pytest 9.1.1, Coverage.py 7.17.0
- Test database: SQLite in-memory (`bbms.settings_test`)
- Scope: executable Python under `apps/`; frontend JavaScript/TypeScript and files outside `apps/` are excluded. No coverage exclusions were configured (0 excluded statements).

## Measured results

Coverage was collected from a fresh complete backend test invocation on `12b8e60`. Result: 650 passed, zero failed, five PostgreSQL-only skips in 65.83 seconds. The five concurrency cases were run separately on PostgreSQL and all passed; they are documented in the [unit report](unit-test-report.md). Coverage is a measurement, not an implied threshold.

| Metric | Covered | Total | Percentage |
|---|---:|---:|---:|
| Statements / executable lines | 2,913 | 3,170 | 91.89% |
| Branches | 517 | 624 | 82.85% |

Coverage.py's combined `Cover` column, which accounts for both statements and branch outcomes, reported 90.41%. It is not the line-only percentage. There were 107 uncovered branch outcomes; no branch exclusions were configured.

## Per-application-package results

| Python package | Covered statements / total | Statement coverage | Covered branches / total | Branch coverage |
|---|---:|---:|---:|---:|
| `accounts` | 390 / 413 | 94.43% | 80 / 94 | 85.11% |
| `adminops` | 332 / 358 | 92.74% | 72 / 88 | 81.82% |
| `audit` | 247 / 253 | 97.63% | 36 / 38 | 94.74% |
| `core` | 344 / 357 | 96.36% | 86 / 98 | 87.76% |
| `donors` | 400 / 429 | 93.24% | 51 / 66 | 77.27% |
| `inventory` | 510 / 620 | 82.26% | 87 / 108 | 80.56% |
| `notifications` | 252 / 274 | 91.97% | 30 / 38 | 78.95% |
| `requests` | 438 / 466 | 93.99% | 75 / 94 | 79.79% |

The package rows aggregate files under each `apps/<package>/` directory; the `apps/__init__.py` package has no executable statements or branches and is omitted from this table.

## Reproduction commands

```powershell
$cov = Join-Path $env:TEMP 'bbms-qa183-12b8e60.coverage'
$json = Join-Path $env:TEMP 'bbms-qa183-12b8e60-coverage.json'
python -m coverage run --data-file=$cov --branch --source=apps -m pytest -q
python -m coverage report --data-file=$cov
python -m coverage json --data-file=$cov -o $json
```

Coverage data and JSON were generated locally in the temporary directory and are not committed. The committed counts above are copied from the generated Coverage.py JSON totals. Repeat the run on the merged #182 revision before calling these evaluation-final measurements.
