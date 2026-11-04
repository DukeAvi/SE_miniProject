# My User Stories and Sprint Tasks

> Source: GitHub issues currently assigned to `avaneesh1830`, including open and closed issues and issues co-assigned with DukeAvi. Sprint, points, status, dependencies, acceptance criteria, and verification requirements are copied from the issues as queried on 4 November 2026. Issue closure is shown as status only; it does not mean the acceptance criteria were independently re-verified for this document.

Implementation work is labeled as a **technical enabler** where it establishes shared or operational capability. Decision and workflow items remain labeled **decision** or **process task**. Entries are ordered by dependencies within each sprint; dependencies outside this document remain listed by issue number.

For the Scrum Master’s request for 1–2 stories per person per sprint, use these two per sprint in the review: **Sprint 1:** #58 and #61; **Sprint 2:** #65 and #66. The other assigned issues remain documented below as supporting work, technical enablers, decisions, or process tasks.

## Sprint 1

### [#86 — OI-3: [Decision] Confirm the blood-unit expiry boundary](https://github.com/DukeAvi/SE_miniProject/issues/86) · Decision

- **Sprint:** 1
- **Story points:** 1
- **GitHub status:** Closed
- **User story:** As a service operator, I need one approved expiry-date and time-zone boundary so that inventory validation, availability searches, and the expiry job use the same rule.
- **Dependencies:**
  - None
- **Acceptance criteria:**
  - [ ] One unambiguous date and time-zone rule is approved.
  - [ ] Exact-boundary examples, approver, and effective date are documented.
  - [ ] Inventory validation, search, and expiry-job ownership is recorded under #59, #61, and #62.
- **Verification requirements:**
  - [ ] Review before, exactly-at, and after-boundary examples.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

### [#91 — OI-8: [Decision] Set operational defaults and retention](https://github.com/DukeAvi/SE_miniProject/issues/91) · Decision

- **Sprint:** 1
- **Story points:** 2
- **GitHub status:** Closed
- **User story:** As a service operator, I need approved operational defaults and their owners documented so that configuration is consistent and can be changed only through authorized settings.
- **Dependencies:**
  - None
- **Acceptance criteria:**
  - [ ] Each required default has an approved value, unit, owner, configuration location, approver, and effective date.
  - [ ] Allowed ranges and fail-closed validation requirements are documented.
  - [ ] Implementation ownership is recorded for appointments #54, low-stock alerts #69, backups #78, and seed data #95.
- **Verification requirements:**
  - [ ] Review threshold, capacity, time-zone boundary, retention, ownership, and validation requirements.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

### [#92 — PROC-001: [Project] Configure the GitHub backlog and sprint board](https://github.com/DukeAvi/SE_miniProject/issues/92) · Process task

- **Sprint:** 1
- **Story points:** 3
- **GitHub status:** Closed
- **User story:** As a Scrum Master, I want the repository backlog and sprint board configured with the agreed planning fields so that the team can see priorities, ownership, and dependencies.
- **Dependencies:**
  - None
- **Acceptance criteria:**
  - [ ] The Project is linked to the repository and contains every published backlog issue.
  - [ ] Backlog, Sprint 1, and Sprint 2 views show status, priority, story points, and ownership when work is claimed.
  - [ ] Every issue belongs to one sprint milestone, has a story-point label, and remains unassigned until a contributor claims it through the agreed workflow.
  - [ ] Blocked work and decision dependencies are visible before implementation starts.
- **Verification requirements:**
  - [ ] Audit the Project item count against backlog/issues.json and check every required planning field.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

### [#93 — PROC-002: [CI] Validate every pull request with GitHub Actions](https://github.com/DukeAvi/SE_miniProject/issues/93) · Process task · technical enabler

- **Sprint:** 1
- **Story points:** 3
- **GitHub status:** Closed
- **User story:** As a developer, I want each pull request and main-branch change validated automatically so that failures are caught and reported before release.
- **Dependencies:**
  - None
- **Acceptance criteria:**
  - [ ] Every pull request triggers the agreed validation workflow.
  - [ ] The workflow uses least-privilege permissions, pinned action versions, dependency caching, and no repository secrets for untrusted code.
  - [ ] A failing test blocks a successful workflow result and provides actionable logs.
  - [ ] The contributing guide lists the local commands corresponding to CI once the application scaffold exists.
- **Verification requirements:**
  - [ ] Open or use a test pull request to capture one passing run and one intentional failing run, then restore the branch to green.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

### [#58 — BBMS-F-020: [Inventory] Create verified blood-unit records](https://github.com/DukeAvi/SE_miniProject/issues/58) · Technical enabler

- **Sprint:** 1
- **Story points:** 5
- **GitHub status:** Closed
- **User story:** As Staff, I want verified donations recorded as uniquely coded blood units so that each collected unit can be tracked in inventory.
- **Dependencies:**
  - `BBMS-F-003`: #52
  - `BBMS-F-011`: #55
- **Acceptance criteria:**
  - [ ] Only Staff can create a verified blood unit linked to an existing completed donation.
  - [ ] Each unit receives a unique unit code suitable for barcode or QR keyboard input.
  - [ ] A valid unit appears in inventory with its initial state and a UNIT_CREATED audit record.
  - [ ] Duplicate codes, unverified donations, missing donations, and forbidden roles are rejected without partial records.
- **Verification requirements:**
  - [ ] Automate TC-Inv-01 for creation, linkage, code uniqueness, scanner input, authorization, and rollback.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

### [#59 — BBMS-F-021: [Inventory] Validate mandatory blood-unit data](https://github.com/DukeAvi/SE_miniProject/issues/59) · Technical enabler

- **Sprint:** 1
- **Story points:** 3
- **GitHub status:** Closed
- **User story:** As Staff, I want mandatory blood-unit details validated consistently so that incomplete or invalid units cannot enter inventory.
- **Dependencies:**
  - `BBMS-F-020`: #58
  - `OI-3`: #86
- **Acceptance criteria:**
  - [ ] Every mandatory inventory field is non-null and validated on the server.
  - [ ] Expiry is after collection, quantity is positive, and blood group and component use the documented enumerations.
  - [ ] Invalid values return field-level errors and save nothing.
  - [ ] Database constraints protect the invariants when application validation is bypassed.
- **Verification requirements:**
  - [ ] Automate TC-Inv-02 across all blood groups and components, date boundaries, quantity boundaries, and direct constraint failures.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

### [#60 — BBMS-F-022: [Inventory] Make stock transitions transactional and auditable](https://github.com/DukeAvi/SE_miniProject/issues/60) · Technical enabler

- **Sprint:** 1
- **Story points:** 8
- **GitHub status:** Closed
- **User story:** As Staff, I want blood-unit state changes recorded transactionally with an immutable ledger so that stock levels remain accurate and auditable.
- **Dependencies:**
  - `BBMS-F-003`: #52
  - `BBMS-F-020`: #58
  - `BBMS-F-021`: #59
- **Acceptance criteria:**
  - [ ] Only documented unit-state transitions are accepted; all others return 409 invalid_state_transition.
  - [ ] Every accepted transition writes exactly one append-only inventory transaction and required audit event atomically.
  - [ ] Available stock always equals the number of unexpired AVAILABLE units and cannot be edited directly.
  - [ ] Concurrent operations cannot reserve or issue one unit twice, and rollback leaves unit, ledger, audit, and stock unchanged.
- **Verification requirements:**
  - [ ] Automate TC-Inv-03 for every valid and invalid transition, rollback, concurrency, and ledger immutability.
  - [ ] Reconcile computed stock against unit and ledger records after the test matrix.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

### [#61 — BBMS-F-023: [Inventory] Search safe blood availability](https://github.com/DukeAvi/SE_miniProject/issues/61)

- **Sprint:** 1
- **Story points:** 3
- **GitHub status:** Closed
- **User story:** As a Recipient, I want to see safe blood availability by group and component so that I can understand whether suitable stock may be available.
- **Dependencies:**
  - `BBMS-F-021`: #59
  - `OI-3`: #86
- **Acceptance criteria:**
  - [ ] Search returns only matching AVAILABLE units whose expiry date is after today under the approved boundary rule.
  - [ ] Staff can view paginated unit-level results while Recipients receive aggregate counts only.
  - [ ] Donors and Admins are denied inventory availability access as defined by the permission matrix.
  - [ ] Invalid blood groups or components return documented validation errors.
- **Verification requirements:**
  - [ ] Automate TC-Inv-04 with all groups and components, expired and near-expiry units, role visibility, empty results, and pagination.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

### [#62 — BBMS-F-024: [Inventory] Run the idempotent daily expiry job](https://github.com/DukeAvi/SE_miniProject/issues/62) · Technical enabler

- **Sprint:** 1
- **Story points:** 5
- **GitHub status:** Closed
- **User story:** As a service operator, I want expiry processing to run safely each day and report its status so that expired units are excluded and job failures can be addressed.
- **Dependencies:**
  - `BBMS-F-022`: #60
  - `OI-3`: #86
- **Acceptance criteria:**
  - [ ] Units at or beyond the approved expiry boundary become EXPIRED and are excluded from availability.
  - [ ] The job is idempotent, cannot overlap for the same run date, and writes ledger and audit records exactly once per unit.
  - [ ] Every run records status, counts, and sanitized error text in job_run.
  - [ ] A partial failure preserves committed batches, reports FAILED, and can be safely rerun.
- **Verification requirements:**
  - [ ] Automate TC-Inv-05 with manipulated dates, exact boundaries, old expiries, repeated runs, overlap attempts, and mid-run failure.
  - [ ] Verify monitoring detects a FAILED run or no successful run within 26 hours.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

### [#97 — PROC-003: [Sprint 1] Record the working-product demonstration](https://github.com/DukeAvi/SE_miniProject/issues/97) · Process task

- **Sprint:** 1
- **Story points:** 2
- **GitHub status:** Closed
- **User story:** As a Scrum Master, I want a short recording of working Sprint 1 flows tied to the tested revision so that reviewers can verify the delivered product and any deviations.
- **Dependencies:**
  - `BBMS-F-002`: #51
  - `BBMS-F-010`: #54
  - `BBMS-F-023`: #61
  - `PROC-002`: #93
- **Acceptance criteria:**
  - [ ] The recording is approximately one minute and shows complete working Sprint 1 flows rather than static screens.
  - [ ] The repository contains or links the recording and identifies the demonstrated revision.
  - [ ] Completed issues and test status are summarized using the sprint template.
  - [ ] Every deviation is documented with impact, rationale, approval status, and follow-up issue.
- **Verification requirements:**
  - [ ] Play the uploaded recording from the repository location and cross-check demonstrated flows against completed Sprint 1 issues.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

## Sprint 2

### [#65 — BBMS-F-032: [Fulfillment] Reserve and issue blood safely](https://github.com/DukeAvi/SE_miniProject/issues/65)

- **Sprint:** 2
- **Story points:** 8
- **GitHub status:** Closed
- **User story:** As Staff, I want compatible available units reserved and issued safely for approved requests so that fulfillment is correct under concurrent use.
- **Dependencies:**
  - `BBMS-F-022`: #60
  - `BBMS-F-031`: #64
  - `BBMS-F-034`: #67
- **Acceptance criteria:**
  - [ ] Reservation selects sufficient compatible AVAILABLE and unexpired units using FEFO and exact-group preference.
  - [ ] Issue rechecks state, availability, expiry, and compatibility inside the locked transaction before fulfillment.
  - [ ] Concurrent requests cannot reserve or issue the same unit, and a repeated idempotency key returns the original result without changing stock twice.
  - [ ] Insufficient stock, incompatibility, invalid state, or unavailable units roll back all allocations, states, ledger, audit, and notifications.
- **Verification requirements:**
  - [ ] Automate TC-Req-03 for FEFO selection, exact-group preference, rollback, concurrency, idempotent retry, and all documented errors.
  - [ ] Run an end-to-end approval, reservation, and issue workflow and reconcile request, unit, allocation, ledger, audit, and stock records.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

### [#66 — BBMS-F-033: [Requests] Show owned request status and history](https://github.com/DukeAvi/SE_miniProject/issues/66)

- **Sprint:** 2
- **Story points:** 3
- **GitHub status:** Closed
- **User story:** As a Recipient, I want to see my request status and its history so that I can understand progress without accessing another person’s request.
- **Dependencies:**
  - `BBMS-F-030`: #63
  - `BBMS-F-031`: #64
- **Acceptance criteria:**
  - [ ] A Recipient can list and view only requests they own, including current status and recorded timestamps.
  - [ ] Another user's request returns the same 404 response as a missing request to prevent identifier enumeration.
  - [ ] Staff can view all requests as allowed by the role matrix; Donors and Admins are denied.
  - [ ] Results are ordered and paginated consistently.
- **Verification requirements:**
  - [ ] Automate TC-Req-04 for ownership, foreign IDs, missing IDs, role access, status history, ordering, and pagination.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

### [#68 — BBMS-F-040: [Notifications] Deliver request status notifications](https://github.com/DukeAvi/SE_miniProject/issues/68) · Technical enabler

- **Sprint:** 2
- **Story points:** 5
- **GitHub status:** Closed
- **User story:** As a Recipient, I want notifications when my request status changes so that I know what action or outcome to expect.
- **Dependencies:**
  - `BBMS-F-031`: #64
  - `OI-7`: #90
- **Acceptance criteria:**
  - [ ] Approved, rejected, held, fulfilled, and other configured status changes create the correct recipient notification exactly once.
  - [ ] Outbox creation commits atomically with the triggering status change.
  - [ ] The worker sends through the selected or mock provider, retries with backoff up to five times, and records sanitized failures.
  - [ ] Users can view only their own notifications, and provider failure never rolls back the clinical action.
- **Verification requirements:**
  - [ ] Automate TC-Notif-01 with the mock provider for each transition, retry, permanent failure, duplicate dispatch protection, ownership, and rollback.
  - [ ] Verify the pending-count and failure-rate monitoring thresholds.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

### [#69 — BBMS-F-041: [Inventory] Alert on configurable low stock](https://github.com/DukeAvi/SE_miniProject/issues/69)

- **Sprint:** 2
- **Story points:** 5
- **GitHub status:** Closed
- **User story:** As Staff, I want low-stock alerts for configured blood groups and components so that I can respond when available stock falls below its threshold.
- **Dependencies:**
  - `BBMS-F-022`: #60
  - `BBMS-F-040`: #68
  - `OI-8`: #91
- **Acceptance criteria:**
  - [ ] Only Admin can view and change valid thresholds, and every change is audited.
  - [ ] A downward threshold crossing creates one low-stock alert for authorized Staff.
  - [ ] Repeated checks below the threshold do not duplicate alerts while alert_active is set.
  - [ ] The alert state clears when stock recovers to or above the threshold, allowing a later crossing to alert again.
- **Verification requirements:**
  - [ ] Automate TC-Notif-02 for every transition around the threshold, repeated checks, recovery, concurrent transactions, configuration authorization, and audit behavior.
  - [ ] Record test commands, results, and sanitized evidence in the pull request.
  - [ ] Update requirement-to-design-to-test traceability where this item changes it.

## Summary

| Issue | Story/task title | Sprint | Points | Status |
| --- | --- | --- | ---: | --- |
| [#86](https://github.com/DukeAvi/SE_miniProject/issues/86) | Decision: [Decision] Confirm the blood-unit expiry boundary | 1 | 1 | Closed |
| [#91](https://github.com/DukeAvi/SE_miniProject/issues/91) | Decision: [Decision] Set operational defaults and retention | 1 | 2 | Closed |
| [#92](https://github.com/DukeAvi/SE_miniProject/issues/92) | Process task: [Project] Configure the GitHub backlog and sprint board | 1 | 3 | Closed |
| [#93](https://github.com/DukeAvi/SE_miniProject/issues/93) | Process task · technical enabler: [CI] Validate every pull request with GitHub Actions | 1 | 3 | Closed |
| [#58](https://github.com/DukeAvi/SE_miniProject/issues/58) | Technical enabler: [Inventory] Create verified blood-unit records | 1 | 5 | Closed |
| [#59](https://github.com/DukeAvi/SE_miniProject/issues/59) | Technical enabler: [Inventory] Validate mandatory blood-unit data | 1 | 3 | Closed |
| [#60](https://github.com/DukeAvi/SE_miniProject/issues/60) | Technical enabler: [Inventory] Make stock transitions transactional and auditable | 1 | 8 | Closed |
| [#61](https://github.com/DukeAvi/SE_miniProject/issues/61) | [Inventory] Search safe blood availability | 1 | 3 | Closed |
| [#62](https://github.com/DukeAvi/SE_miniProject/issues/62) | Technical enabler: [Inventory] Run the idempotent daily expiry job | 1 | 5 | Closed |
| [#97](https://github.com/DukeAvi/SE_miniProject/issues/97) | Process task: [Sprint 1] Record the working-product demonstration | 1 | 2 | Closed |
| [#65](https://github.com/DukeAvi/SE_miniProject/issues/65) | [Fulfillment] Reserve and issue blood safely | 2 | 8 | Closed |
| [#66](https://github.com/DukeAvi/SE_miniProject/issues/66) | [Requests] Show owned request status and history | 2 | 3 | Closed |
| [#68](https://github.com/DukeAvi/SE_miniProject/issues/68) | Technical enabler: [Notifications] Deliver request status notifications | 2 | 5 | Closed |
| [#69](https://github.com/DukeAvi/SE_miniProject/issues/69) | [Inventory] Alert on configurable low stock | 2 | 5 | Closed |
