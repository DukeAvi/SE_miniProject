# OI-8 Operational Defaults and Retention

## Status

Approved by Product Owner Avrit Sharma (`@DukeAvi`) on 2026-10-29 for the version 1.0 classroom demonstration. These synthetic defaults are configurable through deployment configuration and are not clinical or production operating values.

## Decision

Use the defaults below for the version 1.0 demonstration. An invalid value stops the application at startup. It never falls back silently to another value.

| Setting | Default | Unit | Owner | Configuration location | Allowed range and validation |
| --- | --- | --- | --- | --- | --- |
| Blood-bank time zone | `Asia/Kolkata` | IANA time-zone name | Administrator | `BLOOD_BANK_TIME_ZONE` | Must be a valid IANA name |
| Donation slot capacity | `10` | donors per slot | Administrator | `DONATION_SLOT_CAPACITY` | Positive integer; no upper bound approved |
| Low-stock threshold | `5` | units per blood group and component | Administrator | `DEFAULT_STOCK_THRESHOLD` | Positive integer; no upper bound approved |
| Backup retention | `7` | days | Administrator | `BACKUP_RETENTION_DAYS` | Positive integer; no upper bound approved |

## Behavior

- Django's `TIME_ZONE` stays UTC, so timestamps are stored in UTC (SAD risk R9). `BLOOD_BANK_TIME_ZONE` defines the calendar date used by the expiry boundary (OI-3) and donor eligibility checks.
- Per-group stock thresholds are set by the Administrator through the planned threshold configuration (F-041). `DEFAULT_STOCK_THRESHOLD` is the initial value.
- Backup retention of 7 days differs from the 30 days suggested in the SAD. The SAD leaves the value to the team, so this is a deliberate demonstration value. Audit logs keep their separate retention of at least one year (NF-004).

## Consequences

- Seed data (QA-001, issue #95) and the operational runbook must use these values. No runbook exists in the repository yet.
- The low-stock alert (F-041) and the backup job (NF-006) are not implemented yet; this record fixes their defaults only.
- Issue #54 owns appointment capacity, #69 owns low-stock alert thresholds, #78 owns backup retention, and #95 owns synthetic seed data.
- A deployment that needs different values changes the environment variables; no code change is needed.

## Traceability

- Design: SAD Section 4.6, OI-8
- Verification: TC-Notif-02, TC-DR-01; `tests/unit/core/test_operational_defaults.py`
- GitHub: issue #91

## Decision record

- Decision owner and approver: Avrit Sharma, Product Owner (`@DukeAvi`)
- Record contributor: Avaneesh Aroor (`@avaneesh1830`)
- Effective for the classroom demo: 2026-10-29
- References: SAD Sections 3.7 and 4.6; BBMS-NF-004 and BBMS-NF-006; issue #91 comments
