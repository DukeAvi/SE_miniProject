# Final system validation report

Execution date: 2026-11-16. Tested source: `827819fa6b17d283c0886a5a71005935c3aaeddc` (final donor application plus QA-only fixture/connection corrections). Application source matches donor PR #186; subsequent documentation commits do not change that behavior.

Environment: Linux/WSL2, Python 3.13.5, Django 5.2.18, pytest 9.1.1, Coverage.py 7.17.3. Default suite: in-memory SQLite; concurrency checks: disposable PostgreSQL 16 sandbox on loopback, synthetic records only.

## Observed results

| Area | Result and evidence |
| --- | --- |
| Backend regression | 666 passed, zero failed, five SQLite skips; all five separately passed on PostgreSQL |
| Django / migration consistency | System checks passed, no migration drift; audit migration 0007 applied in the disposable browser database |
| API contract | Validated 36 documented operations and 37 Postman requests; 35 operations resolve in Django. The legacy donor-detail design route is superseded by Staff lookup/profile workflows, as recorded in the final SAD amendments. |
| Donor onboarding | Real browser registration, Staff lookup/verification, donor booking/cancellation passed |
| Staff operations | Actual donation, linked unit creation, request approval/reservation/issue passed through the browser and Django API |
| Recipient / privacy | Aggregate availability and request submission passed; invalid form input was preserved and announced in the accessibility tree |
| Admin | Managed Staff-account creation passed through the real UI |
| Accessibility / mobile | All four tested workspaces had zero axe WCAG A/AA violations; keyboard-operated mobile navigation and viewport width checks passed |
| Compatibility / permissions | Full 256 component/pair matrix and 84 role/operation policy cells passed |
| TLS / restart / backup-restore | Existing CI exercises isolated TLS 1.2/1.3, database TLS, process recovery, monitoring rules and encrypted restore. Final successful PR/main run links are retained in the release record. |
| Performance | Existing TC-Perf-01 20-user synthetic benchmark measured search p95 18ms and report p95 16ms, zero failed/non-200 samples; original run 41807600683 and environment are retained in the performance guide. No new benchmark is claimed by this report. |

Browser results: [TC-UX-01](../TC-UX-01.md) and [sanitized browser checks](../evidence/browser-2026-11-16.json). The walkthrough used application source `aca01be`, equivalent to the final donor source after documentation-only additions.

## Explicit limits

Automated accessibility-tree/axe results are not human screen-reader testing or representative-user UAT. A complete month of uptime, production offsite durability/restore timing, and a public production TLS scan were not measured. The existing owner classroom exceptions remain visible in the final RTM and release record, without claiming evaluator approval. No recording is included.

## Historical evidence

The teammate's original preliminary report is preserved at [2026-11-15-system-validation-report.md](history/2026-11-15-system-validation-report.md). Historical failures, skips and measurements are not the current result.
