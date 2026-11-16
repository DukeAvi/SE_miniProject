# Final Branch Coverage Report

## Purpose and measurement

Branch coverage records executed outcomes of application decisions, including `if` conditions, validation branches, role decisions, error paths and retry conditions.

- **Execution date:** 2026-11-16
- **Tested revision:** `827819fa6b17d283c0886a5a71005935c3aaeddc`
- **Tool:** Coverage.py 7.17.3 with `--branch --source=apps`
- **Scope:** backend Python application packages under `apps/`

## Overall result

| Measure | Result |
| --- | ---: |
| Branch outcomes covered | 532 / 646 |
| Branch coverage | 82.35% |
| Missing branch outcomes | 114 |
| Partial branches | 94 |
| Branch exclusions configured | 0 |

The same SQLite run completed 666 tests successfully and skipped five row-lock cases that require PostgreSQL. All five later passed in standalone PostgreSQL runs; those processes are intentionally not mixed into the SQLite coverage percentage.

## Branch coverage by package

| Package | Covered branches | Total branches | Branch coverage | Related behaviour |
| --- | ---: | ---: | ---: | --- |
| accounts | 80 | 94 | 85.11% | Registration, sessions, profile permissions and account security |
| adminops | 72 | 88 | 81.82% | Staff accounts, thresholds and operational reports |
| audit | 36 | 38 | 94.74% | Append-only audit events, search and retention |
| core | 86 | 98 | 87.76% | Permissions, validation, health, monitoring, backup and TLS settings |
| donors | 66 | 88 | 75.00% | Eligibility, appointments, donations and onboarding |
| inventory | 87 | 108 | 80.56% | Unit validation, availability, transitions, expiry and alerts |
| notifications | 30 | 38 | 78.95% | Outbox delivery, retries and failure handling |
| requests | 75 | 94 | 79.79% | Submission, review, history, fulfillment and compatibility rechecks |

## Evidence of decision-path testing

The branch run includes validation and error paths as well as successful flows. Examples include duplicate and full appointments, eligibility boundaries, forbidden roles and foreign-record ownership, invalid unit state transitions, expiry and retention boundaries, request state changes, idempotent issue retries, notification delivery failures, and protected Admin-only operations.

It also runs the complete permission matrix and component compatibility matrix. The PostgreSQL reruns specifically cover competing bookings, duplicate active appointments, competing reservations, same-unit reservation prevention, and single low-stock-alert creation under concurrent reductions.

## Related evidence

Browser behaviour is recorded in [TC-UX-01](../TC-UX-01.md), and deployment/recovery checks are recorded in the [system validation report](system-validation-report.md) and [release record](../release-readiness.md). Requirement-level results are listed in the [RTM](RTM-execution.md).

See the [code coverage report](coverage-report.md) for statement coverage, package statement totals, execution command, and final measurement data.
