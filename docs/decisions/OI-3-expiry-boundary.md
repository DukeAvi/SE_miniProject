# Decision: blood-unit expiry boundary

## Status

Proposed; Product Owner and medical reviewer confirmation is outstanding.

## Context

Issue #86 asks whether a blood unit becomes unavailable at the start of its expiry date or only after that date, and which time zone defines the boundary. SRS BBMS-F-024 says units are marked expired "when their expiry date is reached" by a scheduled daily job, and BBMS-F-023 requires availability search to return only currently available units with expiry filters applied. The SRS does not say whether "reached" means the start or the end of the date. SAD Section 4.6 lists this as OI-3, and the STP Section 5.2 boundary tests depend on the answer.

## Options

1. Expired from the start of the expiry date. A unit with expiry date D is unavailable from 00:00 on D in the blood bank's configured time zone. This is the SAD design rule (Section 4.1.3, DS-023, DS-024) and is the more conservative option.
2. Usable through the end of the expiry date. A unit is unavailable only from 00:00 on D+1. Availability would use `expiry_date >= today` and the daily job `expiry_date < today`, which changes the SAD rule and the boundary tests.

## Decision

For implementation planning, use option 1 as the provisional baseline, following the SAD. This is not formally approved.

A unit is expired when `expiry_date <= today`, where today is the current calendar date in the blood bank's configured time zone (see OI-8), not UTC. Availability queries and reservation apply this rule at query time, independent of the daily job. The daily job (00:05 local time) marks affected units `EXPIRED` and is idempotent.

## Boundary examples

Assumes `expiry_date = 2026-11-10` and the time zone Asia/Kolkata (UTC+05:30), the offset used in the SAD examples. The time zone is pending OI-8.

| Moment | Result |
| --- | --- |
| 2026-11-09 23:59 local | Available; counted in search |
| 2026-11-10 00:00 local | Not available, even before the job runs |
| 2026-11-10 00:05 local | Daily job sets status to EXPIRED |
| 2026-11-11 and later | Remains EXPIRED; re-running the job changes nothing |
| 2026-11-09 18:30 UTC | Same instant as 2026-11-10 00:00 local; not available |

## Consequences

- BBMS-F-023 search returns units with status AVAILABLE and `expiry_date > today` (DS-023).
- BBMS-F-024 job selects AVAILABLE and RESERVED units with `expiry_date <= today` and accepts an `as_of_date` so tests need not wait for real time (SAD Figure 8, STP Section 5.2).
- Issuing a reserved unit whose expiry date has been reached returns 409 `unit_unavailable` (SAD Section 4.3).
- TC-Inv-04 and TC-Inv-05 must cover before, exactly-at, and after the boundary, plus a job failure mid-run.
- If option 2 is chosen instead, the SAD rule, the availability and job queries, and the boundary tests change together.
- SRS F-024 wording and the STP boundary cases need to be updated to match the approved rule. Those documents are not in this repository.

## Approval

- Decision owner: Product Owner (confirmation pending)
- Date: Pending
- Evidence or reference: SRS BBMS-F-023 and BBMS-F-024; SAD Section 3.7 R9, Section 4.1.3, Section 4.6 OI-3; STP Section 5.2; GitHub issue #86
