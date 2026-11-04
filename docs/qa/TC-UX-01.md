# TC-UX-01 — Role dashboards and responsive accessibility

## Execution record

- Project: BBMS, `BBMS-NF-005` / `DS-NF-005`
- Executed: 2026-11-05 (Asia/Kolkata)
- Environment: local Django `bbms.settings_seed` + SQLite synthetic seed; Next.js 16.4.5, React 19.3.0, Node 22.23.2, Codex in-app Chromium browser
- Tested revision: `8366159b92f89609fc2845f7864a67e02a639d53` on `feature/77-role-dashboards` (UI checks used the corresponding local source state before its commit; final lint/typecheck/build/audit ran against this commit).
- Data: only synthetic `.example.test` accounts and the documented `seed_test_data` fixtures. No real donor, recipient, patient, or clinical data was used.

## Results

| Check | Result | Observed evidence / limitation |
| --- | --- | --- |
| Login, role redirect, logout, session and CSRF | Pass (manual) | Synthetic Donor, Recipient, Staff, and Admin accounts each reached their server-returned role route. Logout returned to sign-in. Protected list and read operations loaded through the same-origin API proxy. |
| Donor role view | Partial | Seeded donor profile loaded; own donation history and appointment views rendered; slot search returned capacity. A newly self-registered donor account has no `DonorProfile`, so the existing API returns `404 donor_profile_not_found` for own appointments/history. The signup API does not collect or create the eligibility profile; this is documented, and no client-side substitute was added. |
| Recipient privacy | Pass (manual) | Availability request returned aggregate unit count and nearest expiry only. UI contains no individual unit ID or donor fields. Recipient request form and own-request list rendered. |
| Staff role view | Pass (read path) | Request queue, unit-level inventory, donation recording, unit intake, request workflow controls, and reason-required unit transitions rendered for Staff. No destructive/action mutation was performed in this UI pass. |
| Admin role view | Pass (read path) | Account list, threshold matrix, report date filters/links, audit list, and delivery-failure list loaded. A missing date range was found on first pass; report links now include explicit `from` and `to` dates and are not fetched as part of dashboard initialization. No admin mutation was performed in this UI pass. |
| Labels and accessibility tree | Pass (inspection) | Controls have visible labels or explicit accessible names; icon-only mobile menu has an `aria-label`; table regions and headings appear in the browser accessibility tree. This inspection is not a substitute for NVDA, VoiceOver, or another full screen-reader session. |
| Keyboard navigation and visible focus | Partial | Tab moved through navigation controls; the mobile navigation button exposed expanded/collapsed state and selecting a section closed the menu. CSS provides a 3px `:focus-visible` outline. Full end-to-end keyboard-only operation through every form, table, and native confirmation remains to be verified with a dedicated manual pass. |
| Contrast | Pass for checked theme pairs | Contrast was calculated from the shipped token hex values: muted text `#707069` on paper `#FAF8F2` = 4.70:1; gold-deep `#765300` on white = 6.98:1; focus outline `#946300` on white = 5.19:1; input border `#817D71` on white = 4.11:1. This token check is not a full rendered-page contrast audit. |
| Mobile layout and touch targets | Partial | Recipient dashboard was viewed at 390×844 and donor dashboard at the browser's desktop viewport. Navigation remained reachable through the menu and forms stacked vertically. CSS sets buttons/navigation to at least 44px and inputs to 48px; all component dimensions were not measured individually at runtime. |
| Destructive action confirmation | Implemented; not triggered | Confirm text identifies the unit or request and its relevant attributes. Browser dialogs were not submitted to avoid changing seed state. |
| Desktop/mobile screenshot attachment | Outstanding | Desktop and 390×844 mobile screenshots were captured during the local browser pass, but the current browser interface did not provide a filesystem export path, so image files are not included in this repository report/PR. Do not treat the in-session captures as attached PR evidence. |

## Checks run

```text
cd frontend && npm run lint       — passed
cd frontend && npm run typecheck  — passed
cd frontend && npm run build      — passed (Next.js production build)
cd frontend && npm audit          — passed, 0 vulnerabilities
```

The app was started with the local synthetic SQLite settings; migrations and `seed_test_data --as-of-date 2026-11-05` completed. Browser checks used the real local application and API, not mocked frontend responses. No automated browser test suite or actual screen-reader application was run.

## Known follow-up / release disposition

- Donor self-registration and donor-profile provisioning are separate in the current API. New public registrations cannot use donor appointment/history endpoints until an approved workflow creates a profile.
- `donor_detail` is present in the backend role policy matrix, but no staff donor lookup endpoint is currently registered. Staff donation entry consequently accepts a numeric donor account ID and lets Django validate eligibility; a discoverable donor roster/verification workflow is not implemented in the current API contract.
- Screenshot files and a full keyboard/screen-reader pass remain required before marking the accessibility verification complete.
