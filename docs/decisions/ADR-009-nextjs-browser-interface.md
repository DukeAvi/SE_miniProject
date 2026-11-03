# ADR-009: Add a Next.js browser interface

## Status

Accepted for the Sprint 2 local classroom demonstration. The frontend framework and local-demo scope were selected by the project contributor. The Django API remains the authority for account roles, authorization, validation, state transitions, audit events, and persistence.

## Context

The SRS calls for responsive dashboards for Donor, Recipient, Staff, and Admin. The repository previously delivered the product through Django REST endpoints only and had no browser frontend. The Sprint 2 UX work therefore adds a browser client and changes the implemented component/deployment view. The published SAD source is a PDF with no editable source or generation workflow in this repository.

## Decision

- Build the browser client with Next.js App Router in `frontend/`.
- Keep Django REST Framework as the system of record and business/API layer.
- Use a same-origin Next.js rewrite for `/api/*` requests to the configured Django origin (`BBMS_API_URL`).
- Preserve Django server-side sessions, HttpOnly session cookies, CSRF tokens, and server role permissions. Do not store session or CSRF values in localStorage.
- Keep UI role checks for navigation and clear feedback only; they are not authorization controls.
- Use the warm ivory, gold, charcoal, sage, and restrained crimson visual direction selected for the demo.
- Use synthetic local demo records only.

## Consequences

- Local setup now starts Django and Next.js separately. The frontend documents exact development CSRF origins and the `BBMS_API_URL` setting.
- CI installs the locked frontend dependencies, runs lint and TypeScript checks, builds the app, and audits npm dependencies.
- The implemented user interface covers current API capabilities. It does not invent endpoints where the API lacks an operation; such gaps remain documented in the UX test evidence.
- The published SAD PDF was not regenerated. This ADR records the implementation decision and should be reflected in the next editable SAD revision.

## Traceability

- Requirement: `BBMS-NF-005`
- Design: `DS-NF-005`, SAD sections 3.3–3.4 and 4.5
- Verification: `TC-UX-01`
