# Code Coverage Report — Issue #183 baseline

**Status:** Preliminary measurement; final coverage is pending merge of #182.

## Revision and environment

- Tested revision: `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`
- Execution date: 2026-11-15 (Asia/Calcutta)
- Environment: Windows x64, Python 3.12.7, Django 5.2.18, pytest 9.1.1, Coverage.py 7.17.0
- Test database: SQLite in-memory (`bbms.settings_test`)
- Scope: executable Python under `apps/`; frontend JavaScript/TypeScript and files outside `apps/` are excluded. No coverage exclusions were configured (0 excluded statements).

## Measured results

Coverage was collected from a fresh complete backend test invocation. The test run had the same outcome as the uninstrumented baseline run: 649 passed, 1 failed, 5 skipped, in 62.05 seconds. Coverage includes executed paths up to the failing assertion; this is a measurement, not a quality threshold or a green-suite claim.

| Metric | Covered | Total | Percentage |
|---|---:|---:|---:|
| Statements / executable lines | 2,913 | 3,170 | 91.89% |
| Branches | 517 | 624 | 82.85% |

Coverage.py's combined `Cover` column, which accounts for both statements and branch outcomes, reported 90.41%. It is not the line-only percentage. There were 107 uncovered branch outcomes; no branch exclusions were configured.

## Reproduction commands

```powershell
$cov = Join-Path $env:TEMP 'bbms-qa183-f913.coverage'
$json = Join-Path $env:TEMP 'bbms-qa183-f913-coverage.json'
python -m coverage run --data-file=$cov --branch --source=apps -m pytest -q
python -m coverage report --data-file=$cov
python -m coverage json --data-file=$cov -o $json
```

Coverage data and JSON were generated locally in the temporary directory and are not committed. The committed counts above are copied from the generated Coverage.py JSON totals. Repeat the run on the merged #182 revision before calling these final evaluation measurements.
