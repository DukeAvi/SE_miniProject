# Sprint 1 session expiry acceptance

## Decision

For the API-only Sprint 1 demonstration, BBMS-SR-005 is accepted through the server response: an expired authenticated session returns `401 session_expired` with a readable sign-in message, clears the cookie, and records `SESSION_EXPIRED`. This behavior applies to every role and protected API route. The browser redirect criterion does not apply because Sprint 1 has no browser UI.

## Evidence and traceability

- Requirement: BBMS-SR-005; design: DS-SR-005; verification: TC-Sec-05.
- The SRS requires a configurable inactivity timeout. The merged backend implementation in PR #113 adds the 20-minute idle and eight-hour absolute defaults, sliding renewal, event audit, and the standard response.
- `tests/integration/accounts/test_authentication.py` verifies idle expiry, renewal, absolute expiry, concurrent sessions, disabled accounts, and the response for all four roles.
- Browser redirect and visual accessibility are to be tested when the browser UI is built. This decision does not add a Sprint 2 implementation or change its issue.

## Approval

Product Owner: Avrit Sharma (`DukeAvi`). Approved for the Sprint 1 demo scope on 2026-10-30.
