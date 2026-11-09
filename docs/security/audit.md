# Protected audit records

BBMS-F-051 / DS-051 uses `apps.audit.services.record_event` as the single append path for security and critical-change events. The approved event catalogue is declared by `AuditEvent.Action`. Each row records the actor and role snapshot when known, action, affected record reference when applicable, outcome, source IP, correlation ID, and UTC occurrence time. The helper accepts only catalogued actions and sanitized opaque record identifiers; it has no field for passwords, tokens, session values, patient details, or contact data.

Audit rows are append-only through the application model and query APIs. Business services call the helper inside the same `transaction.atomic()` block as the protected change so both records commit or roll back together.

Only Admin can read audit records. `GET /api/v1/admin/audit-logs` supports these filters:

- `actor`: numeric account ID;
- `action`: approved event action;
- `from` and `to`: inclusive UTC calendar dates;
- `entity_type` and `entity_id`: supplied together for an affected record; and
- `page` and `page_size`, with a maximum page size of 100.

Results are ordered newest first and expose only protected audit metadata. TC-Audit-01 coverage is in `tests/integration/audit/test_audit_search.py`.

## One-year retention (BBMS-NF-004 / DS-NF-004)

Audit events use UTC timestamps and indexed search dimensions: occurrence time,
actor plus time, action plus time, and affected record plus time. Retention uses
the UTC calendar anniversary one year before the run time. An event exactly at
the cutoff is retained; only events strictly older than the cutoff are eligible.
For a leap-day run, the anniversary is February 28 of the preceding year.

Run a safe count-only pass first:

```sh
python manage.py purge_audit_events
```

The command records each run as an `AUDIT_RETENTION_RUN` event. The dry-run is
the default and never deletes records. Review its cutoff and eligible count,
then run the controlled purge explicitly:

```sh
python manage.py purge_audit_events --execute
```

The delete and successful run event are committed in one transaction. A failed
purge rolls back its deletions and records a failure outcome. The command prints
the run identifier, UTC cutoff, eligible count, and deleted count. Schedule it
from the restricted operations environment at least monthly; do not expose a
retention endpoint to application users. The ordinary model and queryset delete
methods remain blocked. `TC-Audit-02` coverage is in
`tests/integration/audit/test_audit_retention.py`.

Search indexes are retained alongside the UTC timestamp. The current ORM model
keeps its single-column generated event identifier because existing audit
lookups and SQLite-based verification rely on it. A PostgreSQL monthly
range-partition conversion would require a coordinated primary-key and schema
migration; it is not part of this issue's explicit verification checklist and
must be reviewed as a separate database-design change before deployment.

## Security-event coverage

BBMS-SR-004 / DS-SR-004 uses the same protected append path for all approved security and critical-change events:

- authentication: `LOGIN_SUCCESS`, `LOGIN_FAILED`, and `SESSION_EXPIRED`;
- account administration: `USER_CREATED`, `USER_DISABLED`, `USER_ENABLED`, and `ROLE_CHANGED`;
- donor operations: `DONOR_UPDATED`, `APPOINTMENT_BOOKED`, `APPOINTMENT_CANCELLED`, and `DONATION_RECORDED`;
- inventory operations: `UNIT_CREATED`, `UNIT_RESERVED`, `UNIT_RELEASED`, `UNIT_ISSUED`, `UNIT_EXPIRED`, `UNIT_DISCARDED`, and `UNIT_RETURNED`;
- request operations: `REQUEST_SUBMITTED`, `REQUEST_APPROVED`, `REQUEST_REJECTED`, `REQUEST_HELD`, and `REQUEST_FULFILLED`; and
- administration and authorization: `THRESHOLD_CHANGED`, `LOW_STOCK_ALERTED`, and `ACCESS_DENIED`.

Failed authentication, expired sessions, and denied access use the `FAILURE` outcome. Known actors retain their role snapshot; unknown-login and expired-cookie events intentionally have no actor. Event rows contain no payload/details field, credentials, token or session value, notification content, or clinical/contact data. Entity references accept only sanitized opaque identifiers.

## Failed-login rate alert

Login throttling and burst alerting are separate controls so blocked attempts still count toward the security alert. More than `FAILED_LOGIN_ALERT_THRESHOLD` failures (default `20`) from one client address inside `FAILED_LOGIN_ALERT_WINDOW_SECONDS` (default `60`) emit one warning to `apps.security.alerts` for that window. The counter stores only a secret-keyed address hash, count, window time, and alert time. The warning is static and includes only the numeric count and window; it contains no address, email, password, token, or session value.

Deployments must route `apps.security.alerts` warnings to their configured alert destination. TC-Sec-04 coverage is in `tests/integration/audit/test_security_events.py`, with feature-level event and rollback coverage in the account, administration, inventory, request, and audit integration suites.
