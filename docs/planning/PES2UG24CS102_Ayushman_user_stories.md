# Ayushman Dey User Stories

- **SRN:** PES2UG24CS102
- **GitHub:** [@ANDYGAMER4321](https://github.com/ANDYGAMER4321)

Issue points below remain the original issue estimates. Issues #54, #55, #76, #77, #95, #96, and #98 are co-assigned with DukeAvi; their estimates are not split between contributors.

## Sprint 1

### S1-US1: Safe donor appointment and donation workflows

As a Donor, I want to find and book an eligible appointment and manage my own bookings, and as Staff, I want to record a completed donation against the correct donor, so that appointment capacity and donation history stay accurate.

**Issues: 17 points**

| Issue | Delivered work | Points |
| --- | --- | ---: |
| [#54](https://github.com/DukeAvi/SE_miniProject/issues/54) | List slots; book, view, and cancel the signed-in donor's appointments | 5 |
| [#55](https://github.com/DukeAvi/SE_miniProject/issues/55) | Record completed donations, update donor history, and record the audit event | 5 |
| [#56](https://github.com/DukeAvi/SE_miniProject/issues/56) | Prevent duplicate active bookings while allowing a valid new booking after cancellation | 2 |
| [#57](https://github.com/DukeAvi/SE_miniProject/issues/57) | Apply shared age, weight, and configured donation-interval eligibility rules | 5 |

**Delivered behavior**

- Booking enforces eligibility, ownership, slot capacity, and duplicate-booking rules.
- Donation recording is Staff-authorized, rechecks eligibility, and saves the immutable donation, donor's last-donation date, and audit event together.
- Donors can view their own appointment and donation history. The browser workflow was completed in Sprint 2 with the donor dashboards and onboarding work.

**Traceability:** SRS BBMS-F-010 through BBMS-F-013; SAD DS-010 through DS-013; STP TC-Don-01 through TC-Don-04.

### S1-US2: Component-aware blood compatibility

As Staff, I want the system to determine donor-recipient compatibility for each supported blood component, so that incompatible combinations are rejected before fulfillment.

**Issue: [#67](https://github.com/DukeAvi/SE_miniProject/issues/67) — 5 points**

**Delivered behavior**

- A shared lookup-driven engine provides component-aware compatibility checks and acceptable donor groups.
- Invalid groups and components fail closed; incompatible combinations return the documented error.
- Automated checks cover all eight ABO/Rh groups against each other for each supported component. Reservation selection, locked rechecks, and rollback remain part of the separate fulfillment workflow.

**Traceability:** SRS BBMS-F-034; SAD DS-034; STP TC-Req-05.

### Supporting Sprint 1 work

| Issue | Delivered work | Points |
| --- | --- | ---: |
| [#84](https://github.com/DukeAvi/SE_miniProject/issues/84) | Approve component-specific compatibility rules used by the compatibility engine | 2 |
| [#85](https://github.com/DukeAvi/SE_miniProject/issues/85) | Approve/configure donation intervals used by eligibility checks | 2 |
| [#90](https://github.com/DukeAvi/SE_miniProject/issues/90) | Select the console/mock notification mode for the classroom demo | 2 |
| [#94](https://github.com/DukeAvi/SE_miniProject/issues/94) | Publish the OpenAPI contract and matching Postman collection | 5 |
| [#95](https://github.com/DukeAvi/SE_miniProject/issues/95) | Provide repeatable synthetic test data and deterministic notification/request mocks | 3 |

## Sprint 2

### S2-US1: Role dashboards and completed donor onboarding

As a BBMS user, I want a responsive workspace for my role, and as a newly registered Donor I want to complete the required profile steps with Staff help, so that I can use appointments and history while Staff can select the correct donor when recording a donation.

**Issues: 13 points**

| Issue | Delivered work | Points |
| --- | --- | ---: |
| [#77](https://github.com/DukeAvi/SE_miniProject/issues/77) | Build Donor, Recipient, Staff, and Admin browser workspaces with responsive layouts and accessible form/navigation patterns | 5 |
| [#182](https://github.com/DukeAvi/SE_miniProject/issues/182) | Add Staff donor lookup and verified-profile creation; connect a newly registered donor to appointments and donation history | 8 |

**Delivered behavior**

- The four role workspaces use the Django session/CSRF API; authorization, ownership, and domain validation remain on the server.
- A new donor receives clear profile-completion guidance. Staff can find the donor, create the verified donor profile, and select the correct donor for donation recording. The donor can then access their own appointment and donation views.
- Browser checks covered the four role workflows, keyboard-operated mobile navigation, form error announcements, and axe WCAG A/AA scans with no reported violations.
- A human screen-reader session and representative-user UAT were not performed; the classroom handoff records them as waived/unperformed.

**Traceability:** SRS BBMS-F-001, BBMS-F-004, BBMS-F-010, BBMS-F-011, BBMS-F-013, BBMS-NF-005, BBMS-SR-002, BBMS-SR-003; SAD DS-001, DS-004, DS-010, DS-011, DS-013, DS-NF-005; STP TC-Auth-01, TC-Profile-01, TC-Don-01, TC-Don-02, TC-Don-04, TC-UX-01, TC-Sec-02, TC-Sec-03.

### S2-US2: Protected audit history and retention

As an Administrator, I want protected audit events to remain searchable and retained for the approved period, so that important actions can be reviewed without allowing ordinary users or application paths to erase recent records.

**Issue: [#76](https://github.com/DukeAvi/SE_miniProject/issues/76) — 5 points**

**Delivered behavior**

- Audit records use UTC timestamps and indexed search fields.
- A controlled purge command supports dry-run and explicit execution, preserves records within the one-year retention window, and records purge outcomes.
- Ordinary model and queryset deletion are blocked. Retention uses indexed queries and controlled deletion rather than physical monthly table partitioning.
- Retention-specific automated checks passed using synthetic records.

**Traceability:** SRS BBMS-NF-004; SAD DS-NF-004; STP TC-Audit-02.

### Supporting Sprint 2 work

| Issue | Delivered work | Points |
| --- | --- | ---: |
| [#96](https://github.com/DukeAvi/SE_miniProject/issues/96) | Execute the test plan and publish the final QA reports and release evidence | 8 |
| [#98](https://github.com/DukeAvi/SE_miniProject/issues/98) | Record final documentation, demo, and freeze disposition for the classroom handoff | 3 |

The final QA report records 666 passed tests and five PostgreSQL-only skips on SQLite; all five concurrency cases also passed in the PostgreSQL run. The repository owner waived the Sprint 2 recording and remaining human acceptance checks for the classroom handoff; they are not described here as performed.

## Project references

- [Sprint 1 summary](../demos/sprint-1-summary.md)
- [Sprint 2 handoff](../demos/sprint-2-summary.md)
- [Software Test Plan](../qa/test-plan.md)
- [UX workflow and accessibility evidence](../qa/TC-UX-01.md)
- [Audit retention evidence](../qa/audit-retention.md)
- [API contract and usage guide](../api/README.md)
