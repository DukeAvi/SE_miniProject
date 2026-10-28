# OI-2 Donation Intervals by Donation Type

## Status

Approved for the classroom demonstration by the assigned contributor under delegated decision authority. This is software demonstration behavior only, not a medical donor-selection policy, and must not be used to guide real donations.

## Decision

Version 1.0 supports whole-blood donations only. The demo requires a minimum of 56 full days between the prior completed whole-blood donation and the appointment or screening date. The configured blood-bank time zone determines calendar dates, and the next eligible date is the previous donation date plus 56 days.

Apheresis plasma, apheresis platelets, and double-red-cell donations are excluded from version 1.0. They must not be represented as eligible donation types or evaluated using the whole-blood interval. Any future support requires a separately reviewed interval and screening policy for that type.

The 56-day value is the existing project requirement for deterministic demonstration behavior. It is not a universal medical recommendation or a claim that 56 days is suitable for every donor or jurisdiction. Before non-demo use, the medical/product owner must set and approve local rules, including any additional donor-specific criteria.

## Configuration and ownership

- Demo default: 56 days for whole blood; unsupported donation types fail closed.
- Change owner: Product Owner with the blood-bank medical reviewer; developers may implement an approved change but do not approve clinical policy.
- Boundary: A donor at exactly 56 full days is interval-eligible; fewer than 56 days is not.
- Other eligibility checks (age at least 18 and screening weight at least 50 kg) remain separate rules and are evaluated on the appointment or screening date.

## Traceability

- Requirements: BBMS-F-013
- Design: DS-013; SAD Section 4.6, OI-2
- Verification: TC-Don-04
- GitHub: issue #85; implementation: issue #57
- Source: Blood Bank Management System SRS, donor eligibility requirements; SAD Sections 4.1.2 and 4.6.

## Decision record

- Approved by: Ayushman Dey, assigned issue contributor acting under delegated decision authority
- Effective for the classroom demo: 2026-10-29
- Medical approval: Not applicable to the mock-data demonstration; required before any real-world use
- Reference: [WHO Blood Donor Selection Guidelines](https://iris.who.int/bitstream/handle/10665/76724/9789241548519_eng.pdf?sequence=1), which describes variation between jurisdictions and donation types and recommends longer whole-blood intervals in its guidance.
