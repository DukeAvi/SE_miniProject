# Branch Coverage Report — Issue #183 baseline

**Status:** Preliminary measurement; final measurement is pending merge of #182.

## Revision and methodology

- Tested revision: `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`
- Execution date: 2026-11-15 (Asia/Calcutta)
- Tool: Coverage.py 7.17.0, `--branch`, Python 3.12.7
- Scope: Python source under `apps/`; frontend code is not included. There are no configured coverage exclusions.
- Test outcome during measurement: 649 passed, 1 failed, 5 skipped in 62.05 seconds. Coverage includes paths executed before the failing assertion.

## Branch results

| Branch outcome metric | Count |
|---|---:|
| Covered branches | 517 |
| Total branches | 624 |
| Branch coverage | 82.85% |
| Uncovered branch outcomes | 107 |
| Excluded branches | 0 |

The measure is branch outcome coverage, not line coverage. The corresponding statement/line measurement is 2,913 of 3,170 (91.89%) and is reported separately in [coverage-report.md](coverage-report.md). No project threshold was specified, so no pass threshold is inferred.

## Reproduction

```powershell
$cov = Join-Path $env:TEMP 'bbms-qa183-f913.coverage'
python -m coverage run --data-file=$cov --branch --source=apps -m pytest -q
python -m coverage report --data-file=$cov
```

The raw coverage data is a temporary local artifact, not committed. Re-run against the merged #182 revision for final evaluation evidence.
