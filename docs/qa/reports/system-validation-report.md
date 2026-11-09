# System Validation Report — Sprint 2 QA

## Current rerun — 2026-11-09

Backend baseline `fd0e96f`: 650 passed, zero failed, five PostgreSQL-only skips (`.venv/bin/pytest -q`, 99.86 seconds). The fixture defect #174 is resolved by merged PR #178. Audit retention is integrated through #176. The current browser review in [TC-UX-01](../TC-UX-01.md) covers four real API-backed role dashboards, axe checks, mobile keyboard navigation, exported desktop/mobile images, and failed-request input preservation.

The workflow includes PostgreSQL low-stock concurrency, TLS deployment, and encrypted backup/restore checks. The original statement below that CI provides no PostgreSQL coverage is superseded. Complete representative-user UAT, actual screen-reader checks, the remaining PostgreSQL concurrency cases, monthly uptime evidence, and owner release sign-off remain unverified. Those are tracked by #96/#77; this report does not invent their outcomes.

## Original execution

**Execution date:** 2026-11-05 (Asia/Kolkata)
**Backend baseline:** `main` `f693371ba0fce6d5d7d57e03ff2aa6dfff47d8f2`
**Dashboard candidate:** PR #177, tree `07039fcf69578034e7bfb966de3e29a9a8ef7375` (same tree as tested dashboard commit `8366159b92f89609fc2845f7864a67e02a639d53`).
**Environment:** Local Django with synthetic SQLite seed data, Next.js 16.4.5 / React 19.3.0, Node 22.23.2, in-app Chromium browser. No personal or clinical production data was used.

## System-level scenarios

| Scenario | Result | Evidence / limitation |
| --- | --- | --- |
| Login, role redirect, session/CSRF proxy, logout for Donor, Recipient, Staff, Admin | Pass (smoke) | Each synthetic role reached its dashboard; protected reads used the Django API. Detailed steps/results: [TC-UX-01](../TC-UX-01.md). |
| Recipient availability privacy | Pass (smoke) | Browser showed aggregate quantity and nearest expiry; no unit or donor identifiers were exposed in the UI response. |
| Donor appointments/history | Partial | Seeded donor profile worked. New public registration does not create a DonorProfile in the current API; this causes the documented profile-not-found response on appointment/history endpoints. |
| Staff work views | Partial | Request/inventory/donation views rendered. No mutating operation was performed in this visual pass. The API currently lacks a staff donor-lookup endpoint. |
| Admin views and reports | Pass (read smoke) | Accounts, thresholds, date-filtered reports, audit and delivery-failure views loaded. No Admin mutation was performed. |
| Responsive/accessibility behavior | Partial | Mobile dashboard navigation and layout were inspected; labels, names, focus token and accessibility tree were reviewed. Full keyboard-only, actual screen-reader, full rendered contrast, and exported screenshot evidence remain outstanding. |
| Automated backend integration | Partial | Full suite on baseline: 506 passed, 1 failed, 5 SQLite-only concurrency tests skipped. Failure is #174. |
| Compatibility safety matrix | Pass (automated) | 64 ABO/Rh pairings for each of four components passed in the automated test suite. |
| Role authorization matrix | Pass (automated) | 84 operation/role cells across 21 operations and four roles passed in the automated test suite. |
| PostgreSQL transaction/concurrency behavior | Not run | Five targeted cases require PostgreSQL row locks and are skipped on SQLite. CI also uses SQLite and does not close this gap. |
| Performance target / availability window | Not run | No controlled JMeter/load sample or monthly uptime measurement was produced. |
| Deployed TLS inspection | Not run | Configuration tests ran; no external endpoint handshake inspection was performed. |
| Backup restore and measured RPO/RTO | Partial | Automated backup/restore-related tests exist and ran; no separately witnessed restore with measured RPO/RTO is attached here. |
| Representative-user UAT | Not run | No UAT participants or acceptance record were provided. |

## Defect and readiness

The one automated failure is the date-sensitive inventory report fixture documented as [#174](https://github.com/DukeAvi/SE_miniProject/issues/174). The GitHub CI run for PR #177 reproduced the same assertion (`inventory_report["count"]` observed `0`, expected `1`). This remains a test/fixture issue pending owner triage; do not treat this report as a green integration build.

This report records smoke and automated evidence only. It does not establish complete system acceptance, UAT, a release recommendation, or freeze approval. System exit criteria remain open pending #174 disposition, PostgreSQL concurrency evidence, external performance/availability/security checks, full accessibility evidence, UAT, and owner sign-off.
