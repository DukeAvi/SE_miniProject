# Branch Coverage Report — Issue #183 baseline

**Status:** Fresh baseline measurement; evaluation-final coverage is pending merge of #182.

## Revision and methodology

- Tested code revision: `12b8e60ab99308fcbd3c92ce1898d952bc440408` (test fixtures/assertions only); application source baseline: `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`
- Execution date: 2026-11-15 (Asia/Calcutta)
- Tool: Coverage.py 7.17.0, `--branch`, Python 3.12.7
- Scope: Python source under `apps/`; frontend code is not included. There are no configured coverage exclusions.
- Test outcome during measurement: 650 passed, 0 failed, 5 PostgreSQL-only skips in 65.83 seconds. All five skipped concurrency cases separately passed on PostgreSQL 16.16.

## Branch results

| Branch outcome metric | Count |
|---|---:|
| Covered branches | 517 |
| Total branches | 624 |
| Branch coverage | 82.85% |
| Uncovered branch outcomes | 107 |
| Excluded branches | 0 |

The measure is branch outcome coverage, not line coverage. The corresponding statement/line measurement is 2,913 of 3,170 (91.89%) and is reported separately in [coverage-report.md](coverage-report.md). No project threshold was specified, so no pass threshold is inferred.

## Branch results by application package

| Python package | Covered branches / total | Branch coverage |
|---|---:|---:|
| `accounts` | 80 / 94 | 85.11% |
| `adminops` | 72 / 88 | 81.82% |
| `audit` | 36 / 38 | 94.74% |
| `core` | 86 / 98 | 87.76% |
| `donors` | 51 / 66 | 77.27% |
| `inventory` | 87 / 108 | 80.56% |
| `notifications` | 30 / 38 | 78.95% |
| `requests` | 75 / 94 | 79.79% |

## Reproduction

```powershell
$cov = Join-Path $env:TEMP 'bbms-qa183-12b8e60.coverage'
python -m coverage run --data-file=$cov --branch --source=apps -m pytest -q
python -m coverage report --data-file=$cov
```

The raw coverage data is a temporary local artifact, not committed. Re-run against the merged #182 revision for evaluation-final evidence.
