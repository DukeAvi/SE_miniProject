# Input validation (BBMS-SR-003 / DS-SR-003 / TC-Sec-03)

Mounted account, donor, and inventory APIs reject undeclared JSON fields and invalid JSON value types before service calls. Choice values, field lengths, dates, UUIDs, and numeric bounds are validated by serializers. Inventory search applies allowlisted filters through the ORM. No application query is assembled by concatenating user input; no rendered user content bypasses Django escaping.

`tests/integration/inventory/test_input_security.py` probes malformed types, extra fields, SQL-shaped strings, template-shaped strings, script-shaped query values, and transition payloads. Account and donor probes are in their existing integration tests. The common type checks live in `apps/core/validation.py`, so later request serializers can use them when those APIs are implemented.

`django.middleware.security.SecurityMiddleware` supplies `X-Content-Type-Options: nosniff`; the application middleware supplies Content-Security-Policy. The request API and browser forms do not exist in Sprint 1, so their owning implementation issues must add equivalent validation and probes when mounted.
