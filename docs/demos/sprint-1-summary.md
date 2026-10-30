# Sprint 1 summary: BBMS Backlog and Sprints

## Sprint goal

Demonstrate the working donor-to-inventory API path: secure session login, appointment booking, completed donation recording, verified inventory creation, and role-limited availability search.

## Completed

- Merged foundations used by the demo include account registration/authentication and role-based access (#50-#58), the API contract (#94), and CI validation (#93). #58 is closed through merged PR #134.
- The exact demonstrated revision `bfd2cec4a88b3f60856293247e6c8b7d038d02ba` contains the BBMS-F-021 validation work from PR #136 and BBMS-F-023 search work from the original PR #138. PR #136 is merged; the search change is under replacement PR #142 after GitHub closed #138 when its base branch was deleted. The demo branch is based on the updated search branch, while this PR's diff contains only the demonstration command and artifacts.
- BBMS-F-022 and BBMS-F-024 are merged through PRs #141 and #139.
- The demo creates synthetic accounts and exercises CSRF-protected login/logout, future appointment search and booking, staff donation recording, verified blood-unit creation, staff search, and recipient aggregate availability. It uses a fresh local SQLite database and fake `example.test` identities.

## Not completed

- BBMS-F-023 #61 remains open in PR #142; its CI is rerunning after the branch was rebased onto the updated `main`.
- PROC-001 #92 remains open for the Scrum Master’s project-owner audit; PR #135 contains the board configuration and audit evidence.
- QA-001 #95 and security follow-ups #80, #81, and #83 remain open in the Sprint 1 milestone.

## Quality status

- Tests executed and pass rate: the full suite on the recorded demo revision passed (290 passed, 2 skipped). After rebasing, the demo command passed again on revision `299653bff4c20c35885f06712f5ecb21a9a51af9` using a fresh synthetic SQLite database. On the updated search branch, inventory search/transition/expiry tests passed (80 passed, 1 skipped); Ruff, Django system checks, and OpenAPI/Postman route validation passed. The skipped tests require PostgreSQL row locks; this environment uses SQLite.
- Open critical or high-priority defects: no defect triage was performed as part of this demonstration; the open stories above remain tracked in GitHub.
- Requirement coverage: the clip demonstrates auth/session, appointment, donation, inventory validation/create/search, and recipient aggregate availability paths. It does not demonstrate stock transitions or the scheduled expiry job.
- Performance, security, accessibility, and recovery status: role separation, session/CSRF behavior, and inventory validation are exercised through integration tests. PostgreSQL concurrency/recovery checks and frontend accessibility are not demonstrated. The repository does not currently contain a browser UI.

## Decisions and deviations

- Presentation format: this repository exposes Django REST endpoints and has no browser UI. The animated GIF is a terminal-style replay of a real, CSRF-protected `APIClient` run against the application views, not a mock UI. It uses synthetic records only. This demonstrates implemented API flows; it does not evaluate browser usability or accessibility.
- Approved SRS/SAD behavior was not changed by the demo. OI-3 expiry behavior is implemented and documented in `docs/decisions/OI-3-expiry-boundary.md`; the daily job is merged through PR #139.
- Product-owner approval for a future browser UI is not implied by this API-focused demonstration.

## Demonstration

- Recording link: [Sprint 1 API walkthrough](sprint-1-demo.gif)
- Duration: 60 seconds
- Tested revision: `bfd2cec4a88b3f60856293247e6c8b7d038d02ba`
- Working flows shown: donor login, slot search and booking, staff login, donation recording, verified inventory creation and search, recipient login and aggregate availability, and logout.

## Next sprint or release actions

1. Review and merge replacement PR #142; then retarget demo PR #140 to `main` and review it.
2. Complete the project-owner audit on #92 and merge #135 when accepted.
3. Finish QA seed data #95 and the open security stories #80, #81, and #83.
4. Decide whether a browser UI is part of the product scope before planning any UI demonstration or accessibility work.
