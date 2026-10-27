# Repository instructions for coding agents

These instructions apply to the entire repository. Read them before inspecting, planning, or changing files.

## Start with the work item

- Work only from a specific GitHub issue. If no issue is identified, ask for one before editing.
- Read the complete issue body, including dependencies, acceptance criteria, verification requirements, requirement ID, design ID, and test ID.
- Do not begin blocked work. Confirm that prerequisite decisions and implementation issues are resolved.
- Keep the issue unassigned. A contributor claims work by commenting on the issue and creating the matching branch.
- Treat the issue as the immediate scope. Do not include unrelated cleanup or another issue's requirements.

## Read the repository sources

Use these sources in order:

1. The selected GitHub issue and its acceptance criteria.
2. `CONTRIBUTING.md` for branch, review, security, and merge rules.
3. The relevant SRS, SAD, and Software Test Plan references.
4. `BACKLOG.md` and `backlog/issues.json` for dependencies and traceability.
5. Existing code, tests, configuration, and nearby documentation.

Local reference documents may exist under `dox/`. That directory is ignored by Git and must never be staged or committed.

If two sources conflict, stop and describe the conflict. Do not silently choose or invent a requirement.

## Branch discipline

- Never implement directly on `main`.
- Use one branch for one issue and one contributor.
- Name branches `<type>/<issue-number>-<short-description>`.
- Allowed branch types are `feature`, `fix`, `test`, `docs`, `security`, and `chore`.
- Start from an up-to-date `main`. If the worktree is dirty, branches have diverged, or updating would overwrite work, stop and ask the contributor what to preserve.
- Do not combine issues on one branch or move unfinished work between teammates' branches.
- Never force-push or rewrite shared history.

When the user asks to implement an identified issue, creating the corresponding local issue branch is allowed if the worktree is clean. Commits, pushes, pull requests, merges, issue changes, and other remote writes require an explicit request.

## Implementation rules

- Follow the architecture and terminology established by the SRS and SAD.
- Keep request handlers thin. Put business rules in services or pure domain functions.
- Enforce authorization and ownership on the server for every protected operation.
- Keep related state changes, inventory ledger entries, audit records, and notification outbox entries in one transaction where required.
- Preserve append-only donation, inventory-ledger, and audit behavior.
- Reuse the shared eligibility and compatibility engines; do not duplicate safety rules in views or UI code.
- Validate all external input and return the documented error format without exposing internal or sensitive details.
- Never commit secrets, tokens, session values, personal data, clinical data, production records, or local environment files.
- Keep changes focused. Do not add dependencies, redesign modules, or alter public contracts unless the issue requires it.

## Tests and evidence

- Add or update tests for every behavioral change.
- Cover success, validation, authorization, ownership, failure, and boundary behavior relevant to the issue.
- Use exhaustive matrices for blood compatibility and role permissions where required.
- Include concurrency, idempotency, transaction rollback, audit, accessibility, performance, or recovery checks when the issue calls for them.
- Run the narrowest relevant checks first, then the broader available suite.
- Run `git diff --check` before handoff.
- Report the exact commands run and their observed results. Never claim a check passed if it was not run.

## Pull-request handoff

- Use `.github/PULL_REQUEST_TEMPLATE.md`.
- Link the issue with `Closes #<issue-number>`.
- Include requirement, design, and test identifiers.
- Explain migrations, API or configuration changes, security implications, and remaining follow-up work.
- Attach screenshots or recordings for visible UI changes and sanitized evidence for safety-critical or non-functional work.
- Request review from `@DukeAvi`.
- Do not self-merge. Only `@DukeAvi` merges into `main`.

## Completion report

At handoff, state:

- the issue addressed and branch used;
- files changed and the behavior delivered;
- tests and checks run, with results;
- assumptions, unresolved questions, risks, and skipped checks; and
- whether any commit, push, pull request, or external change was performed.

Do not mark work complete while acceptance criteria or required verification remain unresolved.
