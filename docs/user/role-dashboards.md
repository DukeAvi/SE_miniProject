# BBMS role dashboard guide

This guide describes the Sprint 2 browser demonstration. Use synthetic information only. Each screen reads and changes data through the Django API; the API performs the authoritative role and ownership checks.

## Start the demo

Follow [the frontend setup guide](../../frontend/README.md) after starting the local Django API. Donor and Recipient accounts can be registered from the sign-in page. Public registration creates the Donor account but does not set verified eligibility details. After a Donor registers, an authorized Staff member searches for the account and records the initial donor profile from the approved verification process. The Donor can then sign in again, refresh the workspace, and use appointment and history views. Profile creation is one-time; duplicate submissions are rejected. A verified profile does not mean the donor is eligible for a particular appointment or donation: the shared eligibility rules are still evaluated. Local seed fixtures remain available for repeatable automated demos. Staff and Admin accounts must be managed through the protected Admin API.

## Donor

- Review and edit your own profile.
- Search available appointment slots by date, book a slot, or cancel one of your own bookings.
- View your own donation history and notifications.

## Recipient

- Check aggregate availability by blood group and component. The page does not show individual units or donor details.
- Submit a blood request and view your own requests and notifications.

## Staff

- Review requests, approve/reject/hold with a reason, reserve compatible stock, and issue reserved units.
- Search unit-level inventory, create a unit from a completed donation, and return or discard eligible units with a reason.
- Record completed donations.
- Search active donor accounts by name or email, verify the initial donor eligibility profile, and select an existing profiled donor for donation recording. The lookup is Staff-only and returns limited account details.
- Staff cannot manage accounts, thresholds, audit records, or delivery failures.

## Admin

- Create and manage Staff/Admin accounts and roles.
- Configure low-stock thresholds, generate reports, review audit events, and inspect notification failures.
- Admin does not approve, reserve, or issue operational blood requests.

## Keyboard and mobile use

All fields have visible labels. Use Tab/Shift+Tab to move through navigation and controls; focus has a visible outline. Mobile navigation has an expanded/collapsed control. Tables can be horizontally scrolled and focused as regions. Status includes text as well as an icon. Success and error feedback use live status/alert regions.
