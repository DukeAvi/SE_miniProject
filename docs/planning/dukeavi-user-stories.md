# DukeAvi's Sprint 1 and Sprint 2 user stories

Contributor: Avrit Sharma ([@DukeAvi](https://github.com/DukeAvi)).

These four stories group the existing issues assigned to DukeAvi for sprint reporting. They do not create additional backlog items or estimates. Points remain on the original issues; each issue appears in only one story total. The linked issues retain their detailed requirements, dependencies and verification criteria.

## Sprint 1

### S1-US1: Secure account access and personal profiles

As a registered user, I want to sign in securely and access only the information and actions allowed for my role, so that I can use the blood bank system without exposing another person's records.

Owner: DukeAvi. Supporting issue total: **26 points**.

| Issue | Supporting work | Existing points |
| --- | --- | ---: |
| [#51](https://github.com/DukeAvi/SE_miniProject/issues/51) | Login, logout and role destinations | 5 |
| [#52](https://github.com/DukeAvi/SE_miniProject/issues/52) | Role permissions and record ownership | 5 |
| [#53](https://github.com/DukeAvi/SE_miniProject/issues/53) | Own-profile viewing and permitted updates | 3 |
| [#80](https://github.com/DukeAvi/SE_miniProject/issues/80) | Authorization in protected endpoints and sensitive services | 5 |
| [#81](https://github.com/DukeAvi/SE_miniProject/issues/81) | Input validation and injection protection | 5 |
| [#83](https://github.com/DukeAvi/SE_miniProject/issues/83) | Idle and absolute session expiry | 3 |

Acceptance criteria:

- Valid credentials create a server-side session and return the correct role destination; invalid credentials receive a generic response and repeated attempts are throttled.
- Logout invalidates the session. Cookies and CSRF protection follow the approved session policy.
- Every protected endpoint and sensitive service enforces the approved role matrix and record ownership.
- Users can read their own profile and change only permitted fields; role, account status and verified medical fields remain protected.
- Invalid or unexpected input is rejected before changes are saved. Session expiry follows the configurable 20-minute idle and eight-hour absolute defaults.

Traceability: DS-002, DS-003, DS-004, DS-SR-002, DS-SR-003 and DS-SR-005; TC-Auth-02, TC-Auth-03, TC-Profile-01, TC-Sec-02, TC-Sec-03 and TC-Sec-05.

Dependencies: registration #50 and the approved role/session decisions #87 and #89. Registration is a dependency, not work attributed to this contributor. Sprint 1 is API-only; a role destination does not claim an implemented browser dashboard.

### S1-US2: Donation records and verified blood availability

As a Staff member, I want eligible donors' appointments and completed donations to feed verified inventory records, so that I can find blood that is available and within its expiry boundary.

Owner: DukeAvi. Supporting issue total: **18 points**.

| Issue | Supporting work | Existing points |
| --- | --- | ---: |
| [#54](https://github.com/DukeAvi/SE_miniProject/issues/54) | Donor appointment booking and cancellation | 5 |
| [#55](https://github.com/DukeAvi/SE_miniProject/issues/55) | Immutable completed-donation records | 5 |
| [#58](https://github.com/DukeAvi/SE_miniProject/issues/58) | Verified blood-unit creation | 5 |
| [#61](https://github.com/DukeAvi/SE_miniProject/issues/61) | Safe availability search | 3 |

Acceptance criteria:

- Eligible donors can book an available slot, view their appointments and cancel their own booked appointment. Concurrent bookings cannot exceed capacity.
- Staff recording a donation uses the shared eligibility engine. The immutable donation, donor date update and audit event commit together.
- Only Staff can create a verified unit linked to a completed donation, with a unique scanner-friendly code and its creation audit event.
- Availability searches filter by blood group and component and exclude units unavailable under the approved status and expiry rules.
- Staff receive paginated unit details; Recipients receive aggregate availability. Other roles are denied, and invalid operations leave no partial records.

Traceability: DS-010, DS-011, DS-020 and DS-023; TC-Don-01, TC-Don-02, TC-Inv-01 and TC-Inv-04.

Dependencies: S1-US1, shared eligibility #57, inventory validation #59 and approved expiry/default decisions #86 and #91. The eligibility engine and other contributors' inventory work remain external dependencies, not additional work credited here.

## Sprint 2

### S2-US1: Blood-request submission and Staff review

As a Staff member, I want recipients' validated blood requests to enter a controlled review queue, so that I can approve, reject or hold each request with a clear decision record.

Owner: DukeAvi. Supporting issue total: **10 points**.

| Issue | Supporting work | Existing points |
| --- | --- | ---: |
| [#63](https://github.com/DukeAvi/SE_miniProject/issues/63) | Recipient request submission | 5 |
| [#64](https://github.com/DukeAvi/SE_miniProject/issues/64) | Staff approval, rejection and hold decisions | 5 |

Acceptance criteria:

- Only Recipients can submit a request. Required patient, blood group, component, units, urgency, hospital, required-by and contact fields are validated.
- A valid submission creates one PENDING request with a unique readable number, timestamp and protected audit record.
- Only Staff can make decisions from permitted source states. Rejection and hold require a non-empty reason.
- State, reviewer, review time, audit entry and required notification outbox entry commit in one transaction.
- Invalid transitions return 409 without changing the request; logs do not expose clinical or contact details.

Traceability: DS-030 and DS-031; TC-Req-01 and TC-Req-02.

Dependencies: authentication and authorization #51/#52 and transactional audit support #72. Notification delivery, request-history presentation and blood reservation/issue are separate issues and are not included in this contributor's story estimate.

### S2-US2: Administrative control and operational oversight

As an administrator, I want controlled Staff access, searchable security records and service health information, so that I can oversee who uses the system and investigate operational problems.

Owner: DukeAvi. Supporting issue total: **18 points**.

| Issue | Supporting work | Existing points |
| --- | --- | ---: |
| [#71](https://github.com/DukeAvi/SE_miniProject/issues/71) | Staff account creation, disabling and role changes | 5 |
| [#72](https://github.com/DukeAvi/SE_miniProject/issues/72) | Protected audit records and Admin search | 5 |
| [#82](https://github.com/DukeAvi/SE_miniProject/issues/82) | Security-event coverage and login-failure alerting | 3 |
| [#74](https://github.com/DukeAvi/SE_miniProject/issues/74) | Readiness, process supervision and availability monitoring | 5 |

Acceptance criteria:

- Only Admin can manage Staff accounts and roles. Disabling an account revokes its active sessions, and role changes apply on the server.
- Critical actions record the applicable actor, role, entity, outcome, UTC time, IP and correlation ID; related business and audit changes commit together.
- Audit records are append-only and searchable only by authorized Admin users, with pagination and documented filters.
- Required security events omit passwords, tokens, session values and unnecessary personal data. More than 20 login failures per minute from one address triggers the configured alert.
- The non-sensitive health endpoint reports readiness; supervised processes recover after failure. One-minute probes, three-failure and five-minute request-error alerts, and maintenance-aware reporting support the 99.5% monthly availability target.

Traceability: DS-050, DS-051, DS-SR-004 and DS-NF-002; TC-Admin-01, TC-Audit-01, TC-Sec-04 and TC-Reli-01.

Dependencies: authorization #52, the Admin/Staff decision #87 and CI foundation #93. Staff-only operational permissions stay separate from Admin permissions. Health monitoring is an operational enabler; this story does not add a monitoring dashboard or claim backup, TLS or performance work owned by other contributors.

## Supporting work outside the four story totals

These assigned tasks support delivery without becoming extra user stories:

- Sprint 1 foundation: [#99](https://github.com/DukeAvi/SE_miniProject/issues/99) (5 points), [#101](https://github.com/DukeAvi/SE_miniProject/issues/101) (2 points).
- Sprint 1 decisions: [#86](https://github.com/DukeAvi/SE_miniProject/issues/86) (1), [#87](https://github.com/DukeAvi/SE_miniProject/issues/87) (1), [#89](https://github.com/DukeAvi/SE_miniProject/issues/89) (1), [#91](https://github.com/DukeAvi/SE_miniProject/issues/91) (2).
- Sprint 1 delivery: [#92](https://github.com/DukeAvi/SE_miniProject/issues/92) (3), [#95](https://github.com/DukeAvi/SE_miniProject/issues/95) (3), [#97](https://github.com/DukeAvi/SE_miniProject/issues/97) (2).
- Other assigned documentation/planning: [#147](https://github.com/DukeAvi/SE_miniProject/issues/147) (1 point; sprint not specified in its body) and [#121](https://github.com/DukeAvi/SE_miniProject/issues/121) (sprint and points not specified). Neither is inserted into a sprint story total.

## Summary

| Sprint | Story | Owner | Supporting issue points |
| --- | --- | --- | ---: |
| 1 | S1-US1: Secure account access and personal profiles | DukeAvi | 26 |
| 1 | S1-US2: Donation records and verified blood availability | DukeAvi | 18 |
| 2 | S2-US1: Blood-request submission and Staff review | DukeAvi | 10 |
| 2 | S2-US2: Administrative control and operational oversight | DukeAvi | 18 |

Sprint story totals: 44 points for Sprint 1 and 28 for Sprint 2. These are reporting rollups, not new estimates or the contributor's complete workload totals.

When working from this document, select one supporting issue, read its full acceptance criteria and prerequisites, and follow CONTRIBUTING.md for its branch and PR. Do not implement an entire grouped story on one branch or change another contributor's issue. The stories describe intended outcomes; execution evidence and delivery status remain in the linked issues and PRs.
