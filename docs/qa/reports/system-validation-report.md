# System Validation Report — Issue #183 baseline

**Status:** Preliminary baseline. Final application and browser validation must use the merged revision of #182. At execution time, #182 was open and assigned to ANDYGAMER4321; this report does not claim validation of its changes.

## Revision and environment

- Tested application revision: `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`
- Execution date: 2026-11-15 (Asia/Calcutta)
- Environment: Windows x64, Python 3.12.7, Django 5.2.18, PostgreSQL 16.16 disposable local instance for the concurrency tests; default backend suite used SQLite in-memory.
- CI evidence: [main CI run 42607673691](https://github.com/DukeAvi/SE_miniProject/actions/runs/42607673691), head `f913fa70a5c6e3b50e07c7f00fc579928508c0ba`, completed successfully 2026-11-09.

## System checks and scenarios

| Scenario | Result | Evidence / limitation |
|---|---|---|
| Django system check | Pass | `python manage.py check --settings=bbms.settings_test`; zero issues. |
| Migration consistency | Pass | `python manage.py makemigrations --check --dry-run --settings=bbms.settings_test`; no changes detected. |
| Ruff | Pass | `python -m ruff check .`; all checks passed. |
| Backend regression suite | Fail | 649 passed, 1 failed, 5 PostgreSQL-only skips on SQLite; see [unit report](unit-test-report.md). |
| GitHub Actions on this report PR | Fail at pytest | Runs [43736538474](https://github.com/DukeAvi/SE_miniProject/actions/runs/43736538474) and [43736855078](https://github.com/DukeAvi/SE_miniProject/actions/runs/43736855078) reproduced the same low-stock `alert_active` assertion (649 passed, 1 failed, 5 skipped); lint, checks and migrations passed. CI ran the SQLite suite, not the PostgreSQL matrix. |
| PostgreSQL concurrency | Partial / failed | All five targeted cases executed on PostgreSQL 16.16: two passed, three failed. The fifth case passed in the baseline GitHub Actions PostgreSQL job; see [run](https://github.com/DukeAvi/SE_miniProject/actions/runs/42607673691). |
| Role permission matrix | Pass (automated baseline) | Existing automated test covers 21 protected operations × four roles (84 cells); included in the full suite. |
| Blood compatibility matrix | Pass (automated baseline) | Existing tests cover 64 ABO/Rh pairings across four components (256 combinations); included in the full suite. |
| Browser and four-role end-to-end flows | Pending #182 | Existing [TC-UX-01 evidence](../TC-UX-01.md) is prior work and is not evidence for #182's donor onboarding or Staff donor-selection changes. Refresh after #182 merges. |
| JMeter performance profile (TC-Perf-01) | Not executed in this run | In CI run 42607673691, JMeter install/profile/artifact steps were skipped by workflow conditions. Successful overall CI is not a performance measurement. Existing [performance procedure](../../operations/performance.md) is procedural documentation, not fresh results. |
| TLS deployment / external endpoint | CI configuration check passed; external production scan unverified | CI job “Verify TLS edge and PostgreSQL TLS deployment” passed in run 42607673691. No public production hostname scan was performed. See [secure transport procedure](../../operations/secure-transport.md). |
| Encrypted backup / restore drill | CI drill passed; production RPO/RTO unverified | CI job “Run encrypted PostgreSQL backup and restore drill” passed in run 42607673691. No production restore or measured production RPO/RTO was performed. See [backup procedure](../../operations/database-backups.md). |
| Monthly 99.5% availability | Not measured | No observed complete month of monitoring data was provided. |
| Human UAT / screen reader | Not performed here | Record only after participants perform and supply results. #182 specifies an updated reproducible UAT/screen-reader checklist. |

## Disposition

This is baseline evidence, not release acceptance. The full suite has one failure, three PostgreSQL cases failed locally, #182's application/browser changes remain unmerged, and production/manual checks remain unverified. No UAT, production TLS scan, production restore drill, or monthly availability claim is made.
