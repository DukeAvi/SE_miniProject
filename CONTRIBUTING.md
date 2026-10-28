# Contributing to BBMS

All work starts from a GitHub issue and reaches `main` through a reviewed pull request. Keep each change small enough to review and test independently.

## Repository layout

Keep changes in the directory that owns them:

- `AGENTS.md` contains repository-wide instructions for coding agents.
- `.github/` contains GitHub issue forms, the pull-request template, and review ownership rules.
- `templates/` contains the reusable issue, PR, test-evidence, decision, and sprint-summary formats.
- `backlog/` contains the stable issue manifest and planning notes used to keep GitHub work traceable.
- `scripts/` contains small repository-maintenance utilities.
- `BACKLOG.md` is the readable backlog index.
- `dox/` is local-only reference material and is ignored by Git; do not add files from it to commits.

Do not create parallel copies of templates or planning files in feature directories. Add source code, tests, migrations, and application documentation under their own application directories once those are introduced.

## Before starting

1. Open the unblocked issue assigned to you and comment that you are starting it. Do not self-assign or change another contributor's assignment.
2. Confirm its acceptance criteria, dependencies, and expected test evidence.
3. Update your local `main` before creating a branch.
4. Work on exactly one issue per branch. Do not share a working branch with another contributor.

Use this branch format:

```text
<type>/<issue-number>-<short-description>
```

Allowed types are `feature`, `fix`, `test`, `docs`, `security`, and `chore`. For example, issue 18 could use `feature/18-inventory-search`.

## While working

- Follow the SRS, SAD, and Software Test Plan in the supplied project references. Local copies may be kept in `dox/`, but `dox/` is intentionally excluded from commits.
- Keep business rules in services or pure domain functions; views should authenticate, validate, and translate.
- Apply server-side authorization to every protected operation. Client-side checks are not security controls.
- Keep state changes, ledger entries, audit records, and notification outbox entries in one transaction where the design requires it.
- Add or update automated tests for every behavioral change.
- Never commit credentials, tokens, personal data, clinical data, production records, or local environment files.
- Coordinate through the issue when an API, migration, shared model, or dependency affects another branch.

Commit messages should be short and action-oriented:

```text
<type>(<area>): <summary>
```

Examples include `feat(inventory): add expiry-safe availability query` and `test(auth): cover inactive session expiry`.

## Local checks

Run these before opening a pull request. They mirror the CI workflow in `.github/workflows/ci.yml`, which runs on every pull request and on pushes to `main`:

'''
python -m pip install -r requirements-dev.txt
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
pytest
git diff --check
'''

CI runs `migrate` against PostgreSQL. Tests use the in-memory SQLite settings in `pytest.ini`.

## Opening a pull request

1. Rebase or merge the latest `main` into your branch and resolve conflicts locally.
2. Run the relevant unit, integration, security, and UI checks.
3. Push only your issue branch.
4. Open a pull request using the repository template.
5. Link the issue with `Closes #<issue-number>`.
6. Include screenshots or recordings for visible UI changes and attach test evidence for safety-critical or non-functional work.
7. Request review from `@DukeAvi`.

Do not merge your own pull request. Only `@DukeAvi` approves and merges changes into `main`. Address review comments on the same branch and request review again after the updates are ready.

## Review checklist

A pull request is ready to merge when:

- the linked issue's acceptance criteria are satisfied;
- automated checks pass;
- requirement, design, and test identifiers remain traceable;
- migrations and API changes are documented;
- no unrelated changes are included;
- security and privacy expectations are met;
- user-facing changes include appropriate accessibility checks; and
- the reviewer has approved the final revision.

## Reporting bugs and security concerns

Use the bug template for ordinary defects. Do not put exploitable security details, credentials, or sensitive records in a public issue; contact the repository owner privately first and create a sanitized tracking issue only when it is safe to do so.
