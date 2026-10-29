# OI-2 Donation Intervals by Donation Type

## Status

Approved for the classroom demonstration by Product Owner Avrit Sharma, recorded on issue #85 on 2026-10-29. This is software demonstration behavior only, not a medical donor-selection policy, and must not be used to guide real donations.

## Decision

Version 1.0 supports whole-blood donations only. The demo requires a minimum of 56 full days between the prior completed whole-blood donation and the appointment or screening date. The configured blood-bank time zone determines calendar dates, and the next eligible date is the previous donation date plus 56 days.

Apheresis plasma, apheresis platelets, and double-red-cell donations are excluded from version 1.0. They must not be represented as eligible donation types or evaluated using the whole-blood interval. Any future support requires a separately reviewed interval and screening policy for that type.

The 56-day value is the existing project requirement for deterministic demonstration behavior. It is not a universal medical recommendation or a claim that 56 days is suitable for every donor or jurisdiction. Before non-demo use, the medical/product owner must set and approve local rules, including any additional donor-specific criteria.

## Configuration and ownership

- Demo defaults: only whole blood is supported; its interval is 56 full days; unsupported donation types fail closed. Eligibility dates use Asia/Kolkata as approved for the mock-data demo under OI-8 (#91).
- Change owner: Product Owner for demo behavior; a qualified medical reviewer must approve any clinical policy before real-world use. Developers implement approved demo changes and do not approve clinical policy.
- Boundary: A donor at exactly 56 full days is interval-eligible; fewer than 56 days is not.
- Safe default: If the donation type is absent or unsupported, reject eligibility rather than applying the whole-blood interval to it.
- Other eligibility checks (age at least 18 and screening weight at least 50 kg) remain separate rules and are evaluated on the appointment or screening date.

## Traceability

- Requirements: BBMS-F-013
- Design: DS-013; SAD Section 4.6, OI-2
- Verification: TC-Don-04
- Ownership: issue #57 owns the pure eligibility engine; #54 owns appointment booking integration; #55 owns completed-donation integration.
- GitHub: decision issue #85; implementation issues #57, #54, and #55
- Source: Blood Bank Management System SRS, donor eligibility requirements; SAD Sections 4.1.2 and 4.6.

## Decision record

- Approved by: Avrit Sharma, Product Owner (approval recorded on issue #85)
- Effective for the classroom demo: 2026-10-29
- Medical approval: This mock-data decision is not medical approval; a qualified reviewer must approve before any real-world use.
- Reference: [WHO Blood Donor Selection Guidelines](https://iris.who.int/bitstream/handle/10665/76724/9789241548519_eng.pdf?sequence=1), which describes variation between jurisdictions and donation types and recommends longer whole-blood intervals in its guidance.
