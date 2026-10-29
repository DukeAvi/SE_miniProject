# Decision: server-side sessions for v1.0 authentication

## Status

Approved for v1.0 classroom demonstration. Product Owner Avrit Sharma recorded approval of option 1 on issue #89 on 2026-10-29.

## Context

Issue #89 asks the team to choose server-side cookie sessions or JWT for v1.0 before the API contract is frozen. The SAD's ADR-004 selects server-side sessions because idle expiry and immediate revocation are simpler. It says JWT may be revisited if an external hospital API client is added.

## Options

1. Use Django server-side sessions in HttpOnly, Secure, SameSite cookies, with CSRF protection for state-changing requests.
2. Use JWT access and refresh tokens, with separate revocation and session-lifetime controls.

## Decision

Use Django server-side sessions in HttpOnly, Secure, SameSite cookies, with CSRF protection for state-changing requests, following SAD ADR-004. External hospital API authentication remains out of scope; adding such a client requires a separate decision.

## Consequences

- The authentication implementation uses Django's server-side session framework and CSRF protection.
- Session cookie security attributes and session lifetime behavior must be configured and tested by BBMS-F-002 and BBMS-SR-005.
- The OpenAPI security scheme and session tests must match the decision before the API contract is frozen.
- No OpenAPI document or editable SRS/SAD source is currently checked in; the repository contains the SAD PDF only.

## Approval

- Decision owner: Avrit Sharma, Product Owner
- Approval: Recorded by Avrit Sharma on issue #89
- Date: 2026-10-29
- Evidence or reference: SAD Section 3.6 and Section 4.6 OI-6 / ADR-004, plus GitHub issue #89
