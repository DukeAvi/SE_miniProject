# BBMS documentation index

This index points to the project documents that are present in the repository and identifies owner-controlled source documents that still need reconciliation. Test outcomes and waivers are recorded in the linked reports; a closed issue does not mean an unperformed check passed.

## Core project documents

- [Project setup and API overview](../README.md)
- [Frontend setup](../frontend/README.md)
- [User guide: role dashboards](user/role-dashboards.md)
- [API guide, OpenAPI contract and Postman collection](api/README.md)
- [Sprint 2 handoff](demos/sprint-2-summary.md)
- [Sprint 2 release-readiness record](qa/release-readiness.md)

## Test plan and QA evidence

- [Software Test Plan - Markdown source, v1.1](qa/test-plan.md)
- [Software Test Plan - submitted PDF, v1.1](../PES2UG24CS102_PES2UG24CS100_PES2UG24CS098_PES2UG24CS101_Test_Plan.pdf)
- [Authoritative requirements traceability matrix](qa/reports/RTM-execution.md)
- [QA-002 execution summary](qa/reports/QA-002-execution-summary.md)
- [System validation report](qa/reports/system-validation-report.md)
- [Unit test report](qa/reports/unit-test-report.md)
- [Line coverage report](qa/reports/coverage-report.md)
- [Branch coverage report](qa/reports/branch-coverage-report.md)
- [TC-UX-01: dashboards and responsive/accessibility evidence](qa/TC-UX-01.md)
- [Desktop and mobile screenshots](qa/screenshots/)
- [Audit retention evidence](qa/audit-retention.md)
- [Synthetic test data guide](qa/seed-test-data.md)

The RTM identifies the exact tested revision and separates current results, historical runs, unperformed checks, and owner-approved classroom waivers. The latest complete backend execution is dated 2026-11-09; this documentation revision does not claim a new application test run.

## Operations and security

- [Availability and health checks](operations/availability.md)
- [Performance target and JMeter procedure](operations/performance.md)
- [Database backup and restore](operations/database-backups.md)
- [Inventory expiry job](operations/inventory-expiry.md)
- [Notifications](operations/notifications.md)
- [Low-stock alerts](operations/low-stock-alerts.md)
- [Secure transport](operations/secure-transport.md)
- [Audit logging and retention](security/audit.md)
- [Authorization model](security/authorization.md)
- [Input validation](security/input-validation.md)

## Architecture decisions

- [Decision records](decisions/)
- [Project backlog and sprint board notes](backlog-project.md)

## Owner-controlled source documents requiring reconciliation

- **SRS v1.0:** referenced by the SAD and the submitted STP, but its PDF is not present in this repository checkout. The RTM uses requirement keys and design/test mappings from `backlog/issues.json` and the committed SAD register. The SRS owner/evaluator must provide or publish the authoritative source for a final verbatim cross-check.
- **SAD v1.0:** the PDF is present at the repository root. Its §3.8.2 still points to the original STP numbering (5.1 compatibility, 5.4 security), while the final plan follows issue #181 (5.1 security, 5.4 compatibility). DukeAvi owns the SAD/SRS reference update; this documentation issue does not edit those PDFs.

The owner-directed 2026-11-09 classroom release closure accepts the limits listed in the release-readiness record. It does not claim production readiness, evaluator sign-off, UAT, actual screen-reader testing, a monthly availability result, or a measured production RPO/RTO.
