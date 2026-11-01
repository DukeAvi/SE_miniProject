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
