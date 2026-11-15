# QA-002 — Final test execution summary (preliminary baseline)

**Status:** Fresh baseline results are recorded; evaluation-final results remain pending. Issue #182 requires the final suite, coverage and refreshed browser evidence to use its merged application revision; #182 remains open and assigned to ANDYGAMER4321.

## Revision, date and environment

- Repository: `DukeAvi/SE_miniProject`
- Tested code revision: `12b8e60` (`test/183-final-qa-reports`; two test-only corrections); application source baseline: `f913fa70a5c6e3b50e07c7f00fc579928508c0ba` (`main` / `origin/main`)
- Execution date: 2026-11-15 (Asia/Calcutta)
- Local environment: Windows x64; Python 3.12.7; Django 5.2.18; pytest 9.1.1; Coverage.py 7.17.0; Ruff installed
- Default backend tests: SQLite in-memory, `bbms.settings_test`
- PostgreSQL concurrency tests: disposable PostgreSQL 16.16 instance, loopback 127.0.0.1:55432, local trust authentication, pytest-created isolated test database; no shared or production database

## Backend test results

| Run | Command | Outcome |
|---|---|---|
| Full backend suite | `python -m pytest -q` | 650 passed, 0 failed, 5 skipped; 54.36s; exit 0 |
| Full suite with coverage | `python -m coverage run --data-file=$cov --branch --source=apps -m pytest -q` | 650 passed, 0 failed, 5 skipped; 65.83s; exit 0 |
| PostgreSQL concurrency | Five separate `python -m pytest --ds=bbms.settings -q <node-id>` runs; exact node commands in [unit-test-report.md](unit-test-report.md) | 5 passed, 0 failed; each actually executed against PostgreSQL 16.16; teardown warnings documented |
| GitHub Actions on report PR #185 | `CI — Lint, checks and tests`, `Run pytest` step | Runs [43736538474](https://github.com/DukeAvi/SE_miniProject/actions/runs/43736538474), [43736855078](https://github.com/DukeAvi/SE_miniProject/actions/runs/43736855078), and [43737103165](https://github.com/DukeAvi/SE_miniProject/actions/runs/43737103165) failed on the same test-fixture date mismatch (649 passed, 1 failed, 5 skipped each). The fixture-only correction is in `12b8e60`; CI for that pushed head is pending. |
| Lint | `python -m ruff check .` | Passed: all checks passed |
| Django checks | `python manage.py check --settings=bbms.settings_test` | Passed: 0 issues |
| Migration consistency | `python manage.py makemigrations --check --dry-run --settings=bbms.settings_test` | Passed: no changes detected |
| Whitespace check | `git diff --check` | Passed |

The five SQLite skips require PostgreSQL locking and are not counted as passes. All five passed in individual fresh-database PostgreSQL runs. A diagnostic combined invocation produced false missing-threshold errors because transaction-test teardown flushed migration-seeded rows between cases; the independent invocations avoid that interference. The third case required a frozen as-of date and a scoped audit-event assertion because the expected low-stock audit event is also emitted. The full-suite CI failure was a stale-date fixture: the API view's imported date alias was not frozen. Both corrections are test-only and are included in `12b8e60`; application behavior was not changed.

## Coverage

Fresh Coverage.py 7.17.0 branch measurement on tested code revision `12b8e60`:

- Statements/executable lines: 2,913 / 3,170 = **91.89%**.
- Branch outcomes: 517 / 624 = **82.85%**; 107 branch outcomes unexecuted.
- Exclusions: 0 configured statements/branches.
- Scope: Python under `apps/` only; no frontend coverage is implied.
- Combined Coverage.py `Cover` metric: 90.41%, distinct from line and branch percentages.

Detailed methods and commands are in [coverage-report.md](coverage-report.md) and [branch-coverage-report.md](branch-coverage-report.md).

## Existing evidence and test matrices

- Role policy: 21 protected operations × four roles (84 cells); included in the full suite.
- Blood compatibility: 64 ABO/Rh pairings × four components (256 combinations); included in the full suite.
- Baseline main CI: [run 42607673691](https://github.com/DukeAvi/SE_miniProject/actions/runs/42607673691) succeeded on `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`. Its PostgreSQL low-stock, TLS edge/PostgreSQL TLS and encrypted backup/restore jobs succeeded. Its JMeter install, normal-load profile and result artifact steps were skipped by workflow conditions; this run does not provide fresh JMeter results.
- Report PR CI failures: each of runs 43736538474, 43736855078 and 43737103165 failed at the same assertion in `test_raising_threshold_can_trigger_alert_and_lowering_it_can_clear_active_state`. The three commits changed report files only. The issue was the test's date patch not reaching the admin view's imported date alias, not a report-code regression. The correction is test-only in `12b8e60`; latest CI on that commit remains to be verified after push.
- Existing browser evidence: [TC-UX-01](../TC-UX-01.md) is historical relative to #182 and must be refreshed after its merge.
- Procedures: [performance/JMeter](../../operations/performance.md), [secure transport](../../operations/secure-transport.md), and [database backup/restore](../../operations/database-backups.md). CI checks are not evidence of an external production TLS scan, production restore with measured RPO/RTO, or a production monthly availability measurement.
- Historical report evidence: prior `f693371` and `fd0e96f` results remain historical and are not relabeled as current. The old report-fixture issue #174 was corrected by merged PR #178; the current low-stock failure is separate.

### Earlier report results (historical)

| Revision / date | Earlier result | Disposition |
|---|---|---|
| `fd0e96f`, 2026-11-09 | 650 passed, 0 failed, 5 SQLite-only skips in 99.86s (historically reported). | Superseded by this fresh 2026-11-15 run; its counts are not attributed to `12b8e60`. |
| `f693371`, 2026-11-05 | 639 passed, 1 failed, 5 skipped; the failure was the date-sensitive operational-report fixture tracked as #174. | #174 was corrected by merged PR #178. This is not the current failure. |

## Requirement coverage and disposition

Automated role and compatibility matrices are represented in the passing full suite. The full backend suite passes with five PostgreSQL-only SQLite skips; all five corresponding PostgreSQL cases pass independently. The test-fixture corrections were not application behavior changes. Evaluation-final measurements still require merged #182 and refreshed donor onboarding/Staff-selection browser flows. Manual UAT and screen-reader execution remain unperformed here. JMeter was not run in the latest baseline CI; no production TLS scan, production restore drill/RPO/RTO, or observed monthly 99.5% availability period is claimed.

No application code was changed. Two test-only corrections fixed nondeterministic/stale test assumptions; the original failures and their CI reruns are documented above. Defect age/severity and release sign-off are not asserted without owner triage and approval. QA-002 evaluation-final acceptance is **not complete** until #182 is merged and the suite, coverage and browser/system checks are rerun on that merged revision. Issue #181 / RTM files were not modified.

## Reproduction

See the exact full-suite, per-case PostgreSQL, Ruff, Django, migration and coverage commands in [unit-test-report.md](unit-test-report.md), [coverage-report.md](coverage-report.md), and [system-validation-report.md](system-validation-report.md). Application source is baseline `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`; tested tree including test-only corrections is `12b8e60`.
