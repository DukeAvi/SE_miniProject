# OI-7 Notification Provider Mode

## Status

Selected for the version 1.0 classroom demonstration. No external delivery provider is configured.

## Decision

Use a console notification adapter for local demonstrations and a deterministic mock adapter in automated tests. Do not send email or SMS to real recipients in version 1.0. This avoids requiring provider accounts, credentials, recipient consent, or an external sandbox for the demonstration.

## Configuration and operational behavior

| Concern | Version 1.0 demo choice |
| --- | --- |
| Provider mode | `NOTIFICATION_PROVIDER=console` |
| Delivery channel | Local console output only; no email or SMS |
| Credentials | None; do not add provider secrets to `.env`, source control, or logs |
| Sandbox | No external sandbox is used. The console adapter is for local demonstration only |
| Rate limits | Not applicable to local console output. Add provider-specific limits before selecting an external service |
| Tests | Inject a deterministic mock adapter; tests cover successful delivery and a simulated failure without network access |
| Failure handling | Keep delivery asynchronous. Retain failed outbox entries for retry with backoff up to five attempts, then mark `FAILED` for Admin review, following the SAD design |

Console output must not include raw notification content, email addresses, phone numbers, tokens, or clinical details. The eventual adapter should emit only sanitized delivery metadata. A provider failure must not roll back the user action that created the notification.

The console mode is not suitable for a deployed service. Selecting email or SMS in a later release requires a separate provider decision, secret-management design, sandbox configuration, rate limits, and delivery-failure review.

## Traceability

- Design: SAD Section 4.6, OI-7
- Verification: TC-Notif-01
- GitHub: issue #90; notification implementation: issue #40; deterministic QA setup: issue #95

## Decision record

- Decision owner: Ayushman Dey, assigned issue contributor
- Effective for the classroom demo: 2026-10-29
- References: SAD Sections 3.2, 4.4, and 4.6; repository issue #90
