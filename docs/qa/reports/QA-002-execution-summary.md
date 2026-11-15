# QA-002 — Final test execution summary (fresh baseline)

**Status:** Fresh baseline evidence is complete for the currently merged application source. Evaluation-final results still depend on #182, which remains open and assigned to ANDYGAMER4321. Do not interpret this report as release acceptance.

## Revision, date and environment

- Repository: `DukeAvi/SE_miniProject`
- Tested code revision: `12b8e60ab99308fcbd3c92ce1898d952bc440408` (`test/183-final-qa-reports`); the two changes since application baseline are test-only fixture/assertion corrections.
- Application source baseline: `f913fa70a5c6e3b50e07c7f00fc579928508c0ba` (`main` / `origin/main` on 2026-11-15)
- Execution date: 2026-11-15 (Asia/Calcutta)
- Local environment: Windows x64, Python 3.12.7, Django 5.2.18, pytest 9.1.1, Coverage.py 7.17.0, Ruff
- Default suite: SQLite in-memory (`bbms.settings_test`)
- PostgreSQL: disposable PostgreSQL 16.16 cluster, loopback `127.0.0.1:55432`, local trust auth; each case used a separate pytest-created test database. No shared or production database was used.

## Backend results

| Run | Result |
|---|---|
| `python -m pytest -q` | 650 passed, 0 failed, 5 skipped in 54.36s; exit 0. Executed-test pass rate 100%; 650/655 collected cases passed (99.24%). |
| `python -m coverage run --data-file=$cov --branch --source=apps -m pytest -q` | 650 passed, 0 failed, 5 skipped in 65.83s; exit 0. |
| Five independent PostgreSQL case runs (`python -m pytest --ds=bbms.settings -q <node-id>`) | 5 passed, 0 failed. Each case truly ran against PostgreSQL; exact node IDs and expected/actual results are in [unit-test-report.md](unit-test-report.md). Each run emitted a test-database teardown warning for two worker sessions; the disposable DB was dropped between cases. |
| Ruff, Django check, migrations, API contracts | All passed: Ruff clean; Django found 0 issues; no migration changes; 34 OpenAPI operations and 35 Postman requests validated, 33 implemented Django operations resolved. |
| `git diff --check` and report links | Passed; no whitespace errors or broken local report links. |

Five concurrency tests are skipped only on the SQLite full-suite backend and are not counted as passes there. The five separate PostgreSQL runs each passed. Running all five in one pytest invocation was attempted as a diagnostic but was not used as the final result: transactional test teardown flushes migration-seeded threshold rows between cases. Separate fresh databases avoid that contamination.

Two test-only corrections were made, without changing application behavior:

- The low-stock threshold test now freezes the date alias imported by the admin API view. Previously only the service module's function was frozen, so the view used 2026-11-15 while fixtures expired 2026-11-10.
- The concurrent inventory test now supplies its frozen business date and scopes its audit assertion to `UNIT_RESERVED`, excluding the expected low-stock audit event.

## CI failure investigation and latest CI

CI runs for commits `5fbf613`, `41c9b62`, and `6e3c1bb`—[43736538474](https://github.com/DukeAvi/SE_miniProject/actions/runs/43736538474), [43736855078](https://github.com/DukeAvi/SE_miniProject/actions/runs/43736855078), and [43737103165](https://github.com/DukeAvi/SE_miniProject/actions/runs/43737103165)—all failed at the same low-stock test assertion: `alert_active` remained true. Each run had 649 passed, 1 failed, and 5 skipped. The three diffs contained only QA reports; no application regression was introduced by those commits. Actual root cause was the stale date fixture described above.

After the fixture corrections, [CI run 43739824521](https://github.com/DukeAvi/SE_miniProject/actions/runs/43739824521) passed on report head `3cc0343a752cb20f67113d540845bb3de175d11b`: backend suite 650 passed / 5 skipped (58.67s), PostgreSQL low-stock case 1 passed (6.88s, teardown warning), Ruff, Django/migration checks, frontend lint/typecheck/build/audit, Compose validation, TLS, monitoring, restart and encrypted backup/restore checks passed. JMeter install/profile/artifact steps were skipped by workflow conditions. This CI head contains the corrected tests and the same application source as `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`; the subsequent report-only documentation commit does not change executable code.

## Coverage

Fresh Coverage.py 7.17.0 run, `--branch --source=apps`:

- Statements / executable lines: **2,913 / 3,170 = 91.89%**.
- Branch outcomes: **517 / 624 = 82.85%**; 107 branch outcomes not covered.
- Exclusions: 0 configured.
- Scope: Python files under `apps/`; frontend code is excluded, not measured.
- Coverage.py combined `Cover` figure: 90.41%; distinct from statement and branch percentages.

Package breakdowns and exact reproduction commands are in [coverage-report.md](coverage-report.md) and [branch-coverage-report.md](branch-coverage-report.md).

## Other evidence and acceptance disposition

- Role policy matrix: 21 operations × four roles (84 cells), included in passing suite.
- Compatibility matrix: 64 ABO/Rh pairs × four components (256 combinations), included in passing suite.
- Performance/JMeter procedure: [performance.md](../../operations/performance.md). No fresh JMeter run; CI steps were skipped.
- TLS procedure: [secure-transport.md](../../operations/secure-transport.md). CI TLS edge and PostgreSQL TLS checks passed; no public production-host scan is claimed.
- Backup/restore procedure: [database-backups.md](../../operations/database-backups.md). CI encrypted synthetic restore/integrity drill passed; no production restore or measured production RPO/RTO is claimed.
- Baseline main CI [42607673691](https://github.com/DukeAvi/SE_miniProject/actions/runs/42607673691) is historical on `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`. It passed configured TLS, backup and PostgreSQL low-stock steps; its JMeter steps were skipped.
- Existing browser evidence [TC-UX-01](../TC-UX-01.md) predates #182 and is not evidence for its donor onboarding/Staff selection changes. Refresh after #182 merges. Manual UAT and screen-reader execution were not performed here.
- No complete observed month was provided; no 99.5% availability claim is made.
- Historical `fd0e96f` (2026-11-09: 650 passed, 0 failed, 5 skipped in 99.86s) and `f693371` (2026-11-05: 639 passed, 1 failed, 5 skipped; date-dependent #174 fixture) are retained as historical only. #174 was corrected by merged PR #178.

System checks and baseline test/coverage evidence are consistent across the four reports. Issue #183 is not evaluation-final until #182 merges and the suite, coverage, and relevant browser/system checks are rerun on that merged application revision. No changes were made to #181's Test Plan, RTM or index files; no product defect was silently changed. Release sign-off, defect aging/severity, production TLS/recovery results, and human UAT remain unasserted.
