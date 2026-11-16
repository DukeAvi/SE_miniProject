# Ayushman Dey — Sprint User Stories

- **Name:** Ayushman Dey
- **SRN:** PES2UG24CS102
- **GitHub:** [@ANDYGAMER4321](https://github.com/ANDYGAMER4321)

## Sprint 1

### S1-US1: Safe donor appointments and completed donation records

As a Donor, I want to book and manage eligible donation appointments, and as Staff, I want to record completed donations accurately, so that donation eligibility, appointment capacity, and donor history remain reliable.

**Supporting issues: 17 points**

| Issue | Work | Points |
| --- | --- | ---: |
| [#54](https://github.com/DukeAvi/SE_miniProject/issues/54) | Schedule, view, and cancel donation appointments | 5 |
| [#55](https://github.com/DukeAvi/SE_miniProject/issues/55) | Record immutable completed donations and update donor history | 5 |
| [#56](https://github.com/DukeAvi/SE_miniProject/issues/56) | Prevent duplicate active appointments | 2 |
| [#57](https://github.com/DukeAvi/SE_miniProject/issues/57) | Apply shared donor eligibility rules | 5 |

**Acceptance criteria**

- Appointment booking uses the shared eligibility engine and does not exceed slot capacity, including under concurrent bookings.
- Donors can view their own appointments and cancel only their own eligible booked appointments.
- Duplicate active appointments are rejected without changing capacity; a cancelled appointment may be booked again where the state rules allow it.
- Only Staff can record a completed donation, and eligibility, required fields, and donation details are validated.
- Donation records are immutable; the donor's last-donation date and audit event are saved atomically with the donation.
- Donors can see their own accurate donation history. Failed or unauthorized operations leave no partial changes.

**Traceability:** DS-010, DS-011, DS-012, DS-013; TC-Don-01, TC-Don-02, TC-Don-03, TC-Don-04.

### Supporting Sprint 1 work

| Issue | Work | Points |
| --- | --- | ---: |
| [#84](https://github.com/DukeAvi/SE_miniProject/issues/84) | Decide compatibility rules by blood component | 2 |
| [#85](https://github.com/DukeAvi/SE_miniProject/issues/85) | Approve donation intervals by donation type | 2 |
| [#90](https://github.com/DukeAvi/SE_miniProject/issues/90) | Select the notification provider mode | 2 |
| [#94](https://github.com/DukeAvi/SE_miniProject/issues/94) | Publish and validate the OpenAPI contract and Postman collection | 5 |
| [#95](https://github.com/DukeAvi/SE_miniProject/issues/95) | Seed synthetic test data and notification mocks | 3 |

## Sprint 2

### S2-US1: Donor onboarding and Staff donor selection

As a newly registered Donor, I want a supported way to complete my donor profile and continue to appointments and history, and as Staff, I want to find and select the correct donor, so that onboarding works for new accounts and donation records are associated with the right person.

**Supporting issue: [#182](https://github.com/DukeAvi/SE_miniProject/issues/182) — 8 points**

**Acceptance criteria**

- A new synthetic donor can complete an authorized profile workflow and reach their own appointment and donation views without fixture-only intervention.
- Incomplete profiles receive clear next steps; the system does not invent medical or eligibility information.
- Protected medical fields and roles cannot be changed through public registration or ordinary profile updates. Eligibility continues to use the shared rules.
- Staff can look up and select the intended donor through the interface, record a donation for that account, and handle invalid or no-match input safely.
- Donor details are exposed only to authorized roles and only as needed for the workflow.
- Regression checks cover success, validation, ownership, authorization, and relevant failure cases; API documentation and user instructions match the implementation.
- Four-role workflow evidence identifies the tested revision. Manual UAT or screen-reader checks are described as complete only when people have actually performed them.

**Traceability:** BBMS-F-001, BBMS-F-004, BBMS-F-010, BBMS-F-011, BBMS-F-013, BBMS-NF-005, BBMS-SR-002, BBMS-SR-003; DS-001, DS-004, DS-010, DS-011, DS-013, DS-NF-005; TC-Auth-01, TC-Profile-01, TC-Don-01, TC-Don-02, TC-Don-04, TC-UX-01, TC-Sec-02, TC-Sec-03.

### Supporting Sprint 2 work

| Issue | Work | Points |
| --- | --- | ---: |
| [#96](https://github.com/DukeAvi/SE_miniProject/issues/96) | Execute the test plan and publish release evidence | 8 |
| [#98](https://github.com/DukeAvi/SE_miniProject/issues/98) | Finalize the demonstration, documentation, and release freeze | 3 |
