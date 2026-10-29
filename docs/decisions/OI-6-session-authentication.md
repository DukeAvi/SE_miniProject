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
- The OpenAPI security scheme is documented in `docs/api/openapi.json`; session tests cover login, CSRF, revocation, and expiry.
- External hospital API authentication remains outside the v1.0 browser-session contract and requires a separate decision if needed.
- No editable SRS/SAD source is checked in; the repository contains the published SAD PDF only.

## Approval

- Decision owner: Avrit Sharma, Product Owner
- Approval: Recorded by Avrit Sharma on issue #89
- Date: 2026-10-29
- Evidence or reference: SAD Section 3.6 and Section 4.6 OI-6 / ADR-004, plus GitHub issue #89

## Published SAD source note

The published SAD PDF still says “Team to confirm” for OI-6. The Product Owner approval recorded on issue #89 supersedes that pending status for v1.0. This decision record supplements the PDF; it does not modify it. The repository contains no editable SAD source or reproducible PDF-generation workflow, so the PDF was not regenerated.
