# BBMS delivery backlog

This index mirrors the GitHub issue backlog derived from the SRS, SAD, Software Test Plan, and Part-2 deliverables. The detailed acceptance and verification criteria live in `backlog/issues.json` and in the published issues.

## Plan summary

| Sprint | Dates | Items | Story points |
| --- | --- | ---: | ---: |
| Sprint 1 | 19-23 October 2026 | 31 | 106 |
| Sprint 2 | 26-30 October 2026 | 18 | 88 |
| Total |  | 49 | 194 |

## Backlog

| Key | Issue | Type | Priority | Sprint | Points | Dependencies |
| --- | --- | --- | --- | ---: | ---: | --- |
| `BBMS-F-001` | [Auth] Register donor and recipient accounts | Implementation | High | 1 | 3 | None |
| `BBMS-F-002` | [Auth] Implement secure login, logout, and role redirects | Implementation | High | 1 | 5 | `BBMS-F-001` |
| `BBMS-F-003` | [Security] Establish role-based access control | Security | High | 1 | 5 | `BBMS-F-002`, `OI-4` |
| `BBMS-F-004` | [Profiles] View and update permitted profile fields | Implementation | Medium | 1 | 3 | `BBMS-F-002`, `BBMS-F-003` |
| `BBMS-F-010` | [Donations] Schedule and cancel donation appointments | Implementation | High | 1 | 5 | `BBMS-F-002`, `BBMS-F-013` |
| `BBMS-F-011` | [Donations] Record immutable completed donations | Implementation | High | 1 | 5 | `BBMS-F-003`, `BBMS-F-013` |
| `BBMS-F-012` | [Donations] Prevent duplicate active appointments | Implementation | High | 1 | 2 | `BBMS-F-010` |
| `BBMS-F-013` | [Donations] Implement donor eligibility rules | Implementation | High | 1 | 5 | `OI-2` |
| `BBMS-F-020` | [Inventory] Create verified blood-unit records | Implementation | High | 1 | 5 | `BBMS-F-003`, `BBMS-F-011` |
| `BBMS-F-021` | [Inventory] Validate mandatory blood-unit data | Implementation | High | 1 | 3 | `BBMS-F-020`, `OI-3` |
| `BBMS-F-022` | [Inventory] Make stock transitions transactional and auditable | Implementation | High | 1 | 8 | `BBMS-F-003`, `BBMS-F-020`, `BBMS-F-021` |
| `BBMS-F-023` | [Inventory] Search safe blood availability | Implementation | High | 1 | 3 | `BBMS-F-021`, `OI-3` |
| `BBMS-F-024` | [Inventory] Run the idempotent daily expiry job | Implementation | High | 1 | 5 | `BBMS-F-022`, `OI-3` |
| `BBMS-F-030` | [Requests] Submit blood requests | Implementation | High | 2 | 5 | `BBMS-F-002`, `BBMS-F-003` |
| `BBMS-F-031` | [Requests] Review and decide blood requests | Implementation | High | 2 | 5 | `BBMS-F-030`, `BBMS-F-051` |
| `BBMS-F-032` | [Fulfillment] Reserve and issue blood safely | Implementation | High | 2 | 8 | `BBMS-F-022`, `BBMS-F-031`, `BBMS-F-034` |
| `BBMS-F-033` | [Requests] Show owned request status and history | Implementation | Medium | 2 | 3 | `BBMS-F-030`, `BBMS-F-031` |
| `BBMS-F-034` | [Safety] Enforce ABO and Rh compatibility | Security | High | 1 | 5 | `OI-1` |
| `BBMS-F-040` | [Notifications] Deliver request status notifications | Implementation | Medium | 2 | 5 | `BBMS-F-031`, `OI-7` |
| `BBMS-F-041` | [Inventory] Alert on configurable low stock | Implementation | High | 2 | 5 | `BBMS-F-022`, `BBMS-F-040`, `OI-8` |
| `BBMS-F-042` | [Reports] Generate operational reports | Implementation | Medium | 2 | 5 | `BBMS-F-011`, `BBMS-F-022`, `BBMS-F-030`, `BBMS-F-032` |
| `BBMS-F-050` | [Administration] Manage staff accounts and roles | Implementation | High | 2 | 5 | `BBMS-F-003`, `OI-4` |
| `BBMS-F-051` | [Audit] Record and search critical actions | Security | High | 2 | 5 | `BBMS-F-003` |
| `BBMS-NF-001` | [Performance] Meet the three-second response target | Quality | High | 2 | 5 | `BBMS-F-023`, `BBMS-F-042` |
| `BBMS-NF-002` | [Reliability] Provide health checks and availability controls | Quality | High | 2 | 5 | `PROC-002` |
| `BBMS-NF-003` | [Security] Protect stored credentials and logs | Security | High | 1 | 3 | `BBMS-F-001`, `BBMS-F-002` |
| `BBMS-NF-004` | [Audit] Retain protected audit records for one year | Quality | High | 2 | 5 | `BBMS-F-051`, `OI-8` |
| `BBMS-NF-005` | [UX] Deliver responsive and accessible role dashboards | Quality | Medium | 2 | 5 | `BBMS-F-004`, `BBMS-F-010`, `BBMS-F-023`, `BBMS-F-033` |
| `BBMS-NF-006` | [Recovery] Automate backups and verify restoration | Quality | High | 2 | 5 | `OI-8` |
| `BBMS-SR-001` | [Security] Enforce TLS and secure transport | Security | High | 2 | 3 | `BBMS-F-002` |
| `BBMS-SR-002` | [Security] Harden server-side authorization | Security | High | 1 | 5 | `BBMS-F-003` |
| `BBMS-SR-003` | [Security] Validate input and prevent injection | Security | High | 1 | 5 | `BBMS-F-001` |
| `BBMS-SR-004` | [Security] Audit security-relevant events | Security | High | 2 | 3 | `BBMS-F-051`, `BBMS-F-050` |
| `BBMS-SR-005` | [Security] Expire idle and long-running sessions | Security | Medium | 1 | 3 | `BBMS-F-002`, `OI-6` |
| `OI-1` | [Decision] Approve compatibility rules by blood component | Decision | High | 1 | 2 | None |
| `OI-2` | [Decision] Approve donation intervals by donation type | Decision | High | 1 | 2 | None |
| `OI-3` | [Decision] Confirm the blood-unit expiry boundary | Decision | High | 1 | 1 | None |
| `OI-4` | [Decision] Confirm separation of Admin and Staff duties | Decision | High | 1 | 1 | None |
| `OI-5` | [Decision] Confirm one role per account for version 1.0 | Decision | Medium | 1 | 1 | None |
| `OI-6` | [Decision] Confirm server-side sessions for version 1.0 | Decision | Medium | 1 | 1 | None |
| `OI-7` | [Decision] Select the notification provider mode | Decision | Medium | 1 | 2 | None |
| `OI-8` | [Decision] Set operational defaults and retention | Decision | High | 1 | 2 | None |
| `PROC-001` | [Project] Configure the GitHub backlog and sprint board | Process | High | 1 | 3 | None |
| `PROC-002` | [CI] Validate every pull request with GitHub Actions | Process | High | 1 | 3 | None |
| `DOC-001` | [API] Freeze the OpenAPI contract and Postman collection | Documentation | High | 1 | 5 | `OI-4`, `OI-6`, `BBMS-F-003` |
| `QA-001` | [QA] Seed complete test data and notification mocks | Quality | High | 1 | 3 | `OI-7`, `OI-8` |
| `QA-002` | [QA] Execute the test plan and publish release evidence | Quality | High | 2 | 8 | `QA-001`, `DOC-001`, `BBMS-NF-001`, `BBMS-NF-006`, `BBMS-SR-004` |
| `PROC-003` | [Sprint 1] Record the working-product demonstration | Process | High | 1 | 2 | `BBMS-F-002`, `BBMS-F-010`, `BBMS-F-023`, `PROC-002` |
| `PROC-004` | [Sprint 2] Finalize the demonstration, documentation, and freeze | Process | High | 2 | 3 | `QA-002` |

## Working agreement

Each issue is implemented on its own branch and merged only through a pull request reviewed by `@DukeAvi`. See `CONTRIBUTING.md` for branch naming, test evidence, review, and merge rules.
