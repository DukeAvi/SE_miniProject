# Sprint 2 release-readiness record

Frozen application revision: `7b66a31` (PR #177 merged). Subsequent handoff documentation does not alter application behavior. On 2026-11-09, the repository owner directed final closure and removal of the recording, accepting the documented verification limits for this classroom handoff.

| Deliverable | Evidence | Disposition |
| --- | --- | --- |
| Integrated browser/API product | PRs #176/#177; [handoff](../demos/sprint-2-summary.md) | Delivered |
| Backend unit/integration tests | [QA summary](reports/QA-002-execution-summary.md), 650 passed / 5 SQLite skips | Automated baseline passes |
| Build, migration, security, deployment checks | [passing PR workflow](https://github.com/DukeAvi/SE_miniProject/actions/runs/42578040297) | Passed on retry |
| Browser and responsive evidence | [TC-UX-01](TC-UX-01.md), four-role desktop/mobile captures | Automated/browser checks pass |
| Actual screen-reader and complete manual UX pass | #77 | Not performed; waived for classroom closure |
| Representative-user UAT | #98 | Not performed; waived for classroom closure |
| Recording | Owner instruction | Removed locally and excluded from publication |
| Final development freeze | #98, owner closure instruction | Application snapshot `7b66a31`, with the limitations below |

QA issue #96 was closed following the evidence PR #175. Its report preserves the original failure and unperformed checks; issue closure does not create new test results. This record supersedes older pending-closure language without changing historical test outcomes.

## Documentation map

- Setup and architecture: [README](../../README.md), [browser architecture decision](../decisions/ADR-009-nextjs-browser-interface.md).
- API and examples: [API guide](../api/README.md), OpenAPI and Postman files alongside it.
- User workflows: [role dashboard guide](../user/role-dashboards.md).
- Tests and traceability: [QA summary](reports/QA-002-execution-summary.md), [RTM](reports/RTM-execution.md), [UX evidence](TC-UX-01.md).
- Operations: [notifications](../operations/notifications.md), [expiry](../operations/inventory-expiry.md), [low-stock alerts](../operations/low-stock-alerts.md), [audit retention](../security/audit.md).
- Deployment/recovery: [secure transport](../operations/secure-transport.md), [backup/restore](../operations/database-backups.md), [availability](../operations/availability.md), [performance](../operations/performance.md).

## Implementation deviations and disposition

| Difference from the submitted/source design | Final disposition |
| --- | --- |
| Browser client added after the original API-only baseline | Next.js client in `frontend/`, recorded in ADR-009; Django retains all authorization and domain rules. Published source PDFs are unchanged. |
| SQLite used for quick demos and most tests | PostgreSQL remains the deployment database. SQLite row-lock skips are explicit; CI separately exercises the low-stock concurrency path on PostgreSQL. |
| Audit retention uses indexed queries and controlled deletion rather than physical monthly partitions | Implemented and tested through #176. Physical partitioning is not claimed. Application model/queryset mutation remains blocked; operators must restrict database credentials. |
| Public donor registration does not provision eligibility profiles | Use the seeded donor profiles for the demonstration; profile provisioning is not silently mocked in the UI. |
| Staff donor lookup is absent from the current API | Donation entry uses the numeric donor account ID, validated by Django. |
| Classroom notification adapter | Console/mock provider per OI-7; no real medical or production notifications. |
| Session expiry simplified for the demo | Approved Sprint 1 session decision remains documented; no stronger production behavior is claimed. |
| Full accessibility certification, UAT, monthly uptime, remaining PostgreSQL concurrency and deployment-specific evidence | Retained as explicit verification limits. Source requirement status must not be rewritten to pass without execution. |

## Closure

The owner instructed final push, merge and issue closure with these limitations documented. This freezes the classroom handoff at the application revision above. Omitted verification is not recorded as passing.
