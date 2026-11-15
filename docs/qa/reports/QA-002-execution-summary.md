# QA-002 — Final test execution summary (preliminary baseline)

**Status:** Issue #183 is in progress. This report records a fresh baseline, not final release evidence. The current issue #182 requires the final suite, coverage and refreshed browser evidence to use its merged application revision; #182 was still open and assigned to ANDYGAMER4321 when these checks ran.

## Revision, date and environment

- Repository: `DukeAvi/SE_miniProject`
- Tested application revision: `f913fa70a5c6e3b50e07c7f00fc579928508c0ba` (`main` / `origin/main` at test time)
- Execution date: 2026-11-15 (Asia/Calcutta)
- Local environment: Windows x64; Python 3.12.7; Django 5.2.18; pytest 9.1.1; Coverage.py 7.17.0; Ruff installed
- Default backend tests: SQLite in-memory, `bbms.settings_test`
- PostgreSQL concurrency tests: disposable PostgreSQL 16.16 instance, loopback 127.0.0.1:55432, local trust authentication, pytest-created isolated test database; no shared or production database

## Backend test results

| Run | Command | Outcome |
|---|---|---|
| Full backend suite | `python -m pytest -q` | 649 passed, 1 failed, 5 skipped; 54.15s; exit 1 |
| Full suite with coverage | `python -m coverage run --data-file=$cov --branch --source=apps -m pytest -q` | 649 passed, 1 failed, 5 skipped; 62.05s; exit 1 |
| Focused PostgreSQL concurrency set | `python -m pytest --ds=bbms.settings -q` plus the five node IDs listed in [unit-test-report.md](unit-test-report.md) | 2 passed, 3 failed; 11.38s; exit 1 |
| GitHub Actions on report PR #185 | CI workflow, `Run pytest` step | Two runs failed with the same low-stock `alert_active` assertion: [43736538474](https://github.com/DukeAvi/SE_miniProject/actions/runs/43736538474) at 5fbf613 (649 passed, 1 failed, 5 skipped; 75.91s) and [43736855078](https://github.com/DukeAvi/SE_miniProject/actions/runs/43736855078) at 41c9b62 (649 passed, 1 failed, 5 skipped; 58.83s). Lint, Django checks, migration checks and migration application passed in both. |
| Lint | `python -m ruff check .` | Passed: all checks passed |
| Django checks | `python manage.py check --settings=bbms.settings_test` | Passed: 0 issues |
| Migration consistency | `python manage.py makemigrations --check --dry-run --settings=bbms.settings_test` | Passed: no changes detected |
| Whitespace check | `git diff --check` | Passed |

The five SQLite skips are explicitly PostgreSQL-only row-lock/concurrency checks and are not passes. On PostgreSQL, duplicate appointment and booking capacity passed; same-unit inventory transition failed because both workers returned conflict instead of one success; request reservation errored because the required stock-threshold row was absent; and low-stock crossing failed because its threshold fixture was absent. A separate CI execution of the fifth test passed on the same baseline in [run 42607673691](https://github.com/DukeAvi/SE_miniProject/actions/runs/42607673691). The full suite's one failure is `test_raising_threshold_can_trigger_alert_and_lowering_it_can_clear_active_state`, which observed `alert_active=True` after lowering the threshold. These failures were not altered or suppressed.

## Coverage

Fresh Coverage.py 7.17.0 branch measurement on this exact revision and test suite:

- Statements/executable lines: 2,913 / 3,170 = **91.89%**.
- Branch outcomes: 517 / 624 = **82.85%**; 107 branch outcomes unexecuted.
- Exclusions: 0 configured statements/branches.
- Scope: Python under `apps/` only; no frontend coverage is implied.
- Combined Coverage.py `Cover` metric: 90.41%, distinct from line and branch percentages.

Detailed methods and commands are in [coverage-report.md](coverage-report.md) and [branch-coverage-report.md](branch-coverage-report.md).

## Existing evidence and test matrices

- Role policy: 21 protected operations × four roles (84 cells); included in the full suite.
- Blood compatibility: 64 ABO/Rh pairings × four components (256 combinations); included in the full suite.
- Latest baseline CI: [run 42607673691](https://github.com/DukeAvi/SE_miniProject/actions/runs/42607673691) succeeded on commit `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`. Its PostgreSQL low-stock, TLS edge/PostgreSQL TLS and encrypted backup/restore jobs succeeded. Its JMeter install, normal-load profile and result artifact steps were skipped by workflow conditions; this run does not provide fresh JMeter results.
- Existing browser evidence: [TC-UX-01](../TC-UX-01.md) is historical relative to #182 and must be refreshed after its merge.
- Procedures: [performance/JMeter](../../operations/performance.md), [secure transport](../../operations/secure-transport.md), and [database backup/restore](../../operations/database-backups.md). CI checks are not evidence of an external production TLS scan, production restore with measured RPO/RTO, or a production monthly availability measurement.
- Historical report evidence: prior `f693371` and `fd0e96f` results remain historical and are not relabeled as current. The old report-fixture issue #174 was corrected by merged PR #178; the current low-stock failure is separate.

### Earlier report results (historical)

| Revision / date | Earlier result | Disposition |
|---|---|---|
| `fd0e96f`, 2026-11-09 | 650 passed, 0 failed, 5 SQLite-only skips in 99.86s (historically reported). | Superseded by this fresh 2026-11-15 run; its counts are not attributed to `f913fa7`. |
| `f693371`, 2026-11-05 | 639 passed, 1 failed, 5 skipped; the failure was the date-sensitive operational-report fixture tracked as #174. | #174 was corrected by merged PR #178. This is not the current failure. |

## Requirement coverage and disposition

Automated role and compatibility matrices are represented in the suite. The local PostgreSQL results explicitly cover all five named row-lock cases, but three failures remain unresolved. System check, migration consistency and lint pass. The backend suite does not pass because of one failure. Fresh final-evaluation measures still require the merged #182 revision, as do refreshed donor onboarding/Staff-selection browser flows. Manual UAT and screen-reader execution remain unperformed here. JMeter was not run in the latest baseline CI; no production TLS scan, production restore drill/RPO/RTO, or observed monthly 99.5% availability period is claimed.

No product code or tests were changed for this reporting task, so no product defect was silently fixed. Defect age/severity and release sign-off are not asserted without owner triage and approval. QA-002 acceptance is **not complete** until #182 is merged, all final runs are repeated, and the failing tests are dispositioned. Issue #181 / RTM files were not modified.

## Reproduction

See the exact full-suite, PostgreSQL, Ruff, Django, migration and coverage commands in [unit-test-report.md](unit-test-report.md), [coverage-report.md](coverage-report.md), and [system-validation-report.md](system-validation-report.md). All results above refer to revision `f913fa70a5c6e3b50e07c7f00fc579928508c0ba` only.
