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
