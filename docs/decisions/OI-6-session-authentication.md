# Decision: server-side sessions for v1.0 authentication

## Status

Proposed; team confirmation is outstanding.

## Context

Issue #89 asks the team to choose server-side cookie sessions or JWT for v1.0 before the API contract is frozen. The SAD's ADR-004 selects server-side sessions because idle expiry and immediate revocation are simpler. It says JWT may be revisited if an external hospital API client is added.

## Options

1. Use Django server-side sessions in HttpOnly, Secure, SameSite cookies, with CSRF protection for state-changing requests.
2. Use JWT access and refresh tokens, with separate revocation and session-lifetime controls.

## Decision

For implementation planning, use option 1 as the provisional v1.0 browser authentication mechanism, following SAD ADR-004. This is not formally approved. External hospital API authentication remains out of scope unless separately approved; adding such a client requires revisiting this decision.

## Consequences

- The authentication implementation uses Django's server-side session framework and CSRF protection.
- Session cookie security attributes and session lifetime behavior must be configured and tested by BBMS-F-002 and BBMS-SR-005.
- The OpenAPI security scheme and session tests must match the decision before the API contract is frozen.
- No OpenAPI document or editable SRS/SAD source is currently checked in; the repository contains the SAD PDF only.

## Approval

- Decision owner: Project team (confirmation pending)
- Date: Pending
- Evidence or reference: SAD Section 3.6 and Section 4.6 OI-6 / ADR-004, plus GitHub issue #89
