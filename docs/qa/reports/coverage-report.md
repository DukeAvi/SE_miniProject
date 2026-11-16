# Final Code Coverage Report

## Measurement scope

- **Execution date:** 2026-11-16
- **Tested revision:** `827819fa6b17d283c0886a5a71005935c3aaeddc`
- **Tooling:** Python 3.13.5, pytest 9.1.1, Coverage.py 7.17.3
- **Command:** `python -m coverage run --branch --source=apps -m pytest -q`
- **Measured scope:** executable Python in `apps/`

This is backend application coverage for executable Python under `apps/`.

## Overall result

| Measure | Covered | Total | Result |
| --- | ---: | ---: | ---: |
| Statements / executable lines | 3,036 | 3,297 | 92.08% |
| Branch outcomes | 532 | 646 | 82.35% |
| Combined Coverage.py figure | — | — | 90.49% |
| Excluded executable lines | 0 | — | 0% |

The measured run executed 666 tests successfully and skipped five PostgreSQL-only row-lock tests under SQLite. All five were subsequently executed against PostgreSQL and passed; those independent processes are not included in the SQLite coverage percentage.

## Package coverage

| Package | Statements covered | Statement coverage | Branches covered | Branch coverage |
| --- | ---: | ---: | ---: | ---: |
| accounts | 390 / 413 | 94.43% | 80 / 94 | 85.11% |
| adminops | 332 / 358 | 92.74% | 72 / 88 | 81.82% |
| audit | 252 / 258 | 97.67% | 36 / 38 | 94.74% |
| core | 344 / 357 | 96.36% | 86 / 98 | 87.76% |
| donors | 518 / 551 | 94.01% | 66 / 88 | 75.00% |
| inventory | 510 / 620 | 82.26% | 87 / 108 | 80.56% |
| notifications | 252 / 274 | 91.97% | 30 / 38 | 78.95% |
| requests | 438 / 466 | 93.99% | 75 / 94 | 79.79% |

## What the coverage run exercises

The 671 collected automated cases exercise registration and sessions; role and ownership policy; donor eligibility, appointment booking and donations; inventory validation, search, transitions and expiry; requests, fulfillment and component compatibility; notifications; reporting; administration; audit retention; security controls; and operational configuration.

The final test suite also includes:

- 84 role-operation policy checks across the four application roles;
- 256 donor/recipient blood-group and component compatibility combinations;
- exact time and date boundaries for eligibility, expiry, retention and session behavior;
- rollback and append-only checks for donations, inventory, requests, audit events and notifications; and
- five dedicated PostgreSQL concurrency checks, recorded separately from SQLite coverage.

## Coverage analysis

The raw measurement contains 261 uncovered statements, 114 missing branch outcomes and 94 partial branches. No executable lines were excluded.

The lowest package results are donor branch outcomes (75.00%), notification branch outcomes (78.95%), request branch outcomes (79.79%), and inventory statements/branches (82.26% / 80.56%). Requirement results are listed in the [RTM](RTM-execution.md).

## Supporting evidence

- [Unit and integration test report](unit-test-report.md): execution totals and PostgreSQL reruns.
- [Branch coverage report](branch-coverage-report.md): branch-specific interpretation.
- [Final execution data](../evidence/final-execution.json): durable sanitized measurement totals.
- [System validation report](system-validation-report.md): browser, CI, deployment and operational checks outside this Python measurement.
