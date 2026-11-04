# QA-002 — Sprint 2 test execution summary

**Execution date:** 2026-11-05 (Asia/Kolkata)
**Tested baseline:** `main` at `f693371ba0fce6d5d7d57e03ff2aa6dfff47d8f2`
**Environment:** Linux, Python 3.14.6, Django 5.2.18, pytest 9.1.1, SQLite in-memory test database (`bbms.settings_test`).
**Data:** the automated suite uses its isolated synthetic fixtures. No production or personal donor/recipient records were used.

## Execution result

| Measure | Result |
| --- | ---: |
| Collected | 645 / 645 (100%) |
| Passed | 639 |
| Failed | 1 |
| Skipped / blocked by SQLite backend | 5 |
| Pass rate among executed tests | 639 / 640 = 99.84% |
| Pass rate among all collected tests | 639 / 645 = 99.07% |

The five skipped cases explicitly require PostgreSQL row locking or concurrent transaction behavior. They are not counted as passes. The failed case is `tests/integration/adminops/test_operational_reports.py::test_admin_gets_grouped_summaries_without_staff_level_record_access`; isolated reproduction also failed. It expects an inventory transaction dated 2026-11-04, but its fixture lets `occurred_at` default to the current time (2026-11-05). The report correctly filters the requested prior-day window, so the test sees zero rows. Tracking issue [#174](https://github.com/DukeAvi/SE_miniProject/issues/174) records the failure. This is currently classified as a time-dependent test-fixture defect; it does not alone demonstrate an endpoint defect. Severity and owner triage remain pending.

The initial full run and isolated reproduction were retained as the first failed outcomes. The second full run under coverage reproduced the same failure; no code or test was modified between runs.

## Role and compatibility matrices

- Server role permissions: `tests/unit/core/test_permissions.py::test_role_matrix_matches_sad_and_is_enforced_for_every_role_cell` checks 21 protected operation codes against Donor, Recipient, Staff, and Admin (84 role-operation cells), compares the configured policy with the expected SAD matrix, and checks access-denial audit records. **Pass** on this baseline.
- Blood compatibility: `tests/unit/requests/test_compatibility.py` exercises all 64 ABO/Rh donor-recipient pairings for each of four components (256 component/pair combinations), invalid values, and incompatible fulfillment rejection. **Pass** on this baseline.
- Browser role checks and responsive evidence are recorded in [TC-UX-01](../TC-UX-01.md). Those checks are **partial**: screen-reader and full keyboard-only passes and screenshot files remain outstanding.

## Candidate revisions outside the baseline

The tested baseline does not include either open dashboard/retention PR. Keep these results separate from the baseline result:

- Audit-retention candidate: PR [#172](https://github.com/DukeAvi/SE_miniProject/pull/172), head `0aba4807f882e8e9c95430f845a9028d64cd173d`. Its prior branch run reported 650 passed and 5 SQLite skips. It is unmerged; this is candidate evidence, not evidence that `main` contains the change.
- Dashboard candidate: PR [#173](https://github.com/DukeAvi/SE_miniProject/pull/173), head `0af92d6d8d477c73bce15875689314618078ce6f`. Frontend lint, typecheck, production build, and dependency audit passed; local browser checks and remaining accessibility limits are in [TC-UX-01](../TC-UX-01.md). It is an open draft and not integrated into this baseline.

## Defect and release disposition

One test-fixture defect is open (#174), first observed and filed on 2026-11-05. Defect aging is 0 calendar days at this report timestamp. The ratio 1/645 (0.16%) is a **test-case failure ratio**, not a product defect-density estimate; no valid size denominator or triaged product-defect inventory exists. No critical product defect was demonstrated by this run, but a complete critical-defect review has not been signed off.

UAT, external TLS inspection, the performance/load target, monthly availability evidence, and final owner sign-off have not been evidenced here. The QA exit criteria therefore remain **not satisfied**. Do not treat this as a release recommendation or freeze approval.

## Reproduction commands

Run from the repository root with the project QA virtual environment:

```text
/tmp/bbms-sprint2-venv/bin/python -m pytest --collect-only -q
/tmp/bbms-sprint2-venv/bin/python -m pytest -q
/tmp/bbms-sprint2-venv/bin/python -m pytest -q tests/integration/adminops/test_operational_reports.py::test_admin_gets_grouped_summaries_without_staff_level_record_access -vv
```

The full baseline run took 136.24 seconds without coverage and 146.24 seconds with coverage. The isolated reproduction took 1.29 seconds.
