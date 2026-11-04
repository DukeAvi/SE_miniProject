# Requirements Traceability — Sprint 2 QA

**Tested baseline:** `main` `f693371ba0fce6d5d7d57e03ff2aa6dfff47d8f2` (2026-11-05, Asia/Kolkata).
**Source:** Team 9 BBMS SRS v1.0, §8 RTM; Software Test Plan §5 and §13.
**Status key:** **P** = automated evidence passed on the stated baseline; **F** = failed test requiring triage; **Partial** = some evidence exists but acceptance is not fully verified; **NR** = not run or no sufficient evidence. These are execution dispositions, not edits to the original SRS.

| Requirement | Planned case | Result | Evidence / limitation |
| --- | --- | --- | --- |
| BBMS-F-001 | TC-Auth-01 | P | `tests/integration/accounts/test_registration.py` |
| BBMS-F-002 | TC-Auth-02 | P | `tests/integration/accounts/test_authentication.py` |
| BBMS-F-003 | TC-Auth-03 | P | 84-cell server permission matrix in `tests/unit/core/test_permissions.py` |
| BBMS-F-004 | TC-Profile-01 | P | `tests/integration/accounts/test_profile.py` |
| BBMS-F-010 | TC-Don-01 | P | `tests/integration/donors/test_appointment_booking.py`; SQLite concurrency cases separately skipped |
| BBMS-F-011 | TC-Don-02 | P | `tests/integration/donors/test_donation_recording.py` |
| BBMS-F-012 | TC-Don-03 | P | `tests/integration/donors/test_appointment_booking.py` |
| BBMS-F-013 | TC-Don-04 | P | `tests/unit/donors/test_eligibility.py` and donor integration tests |
| BBMS-F-020 | TC-Inv-01 | P | `tests/integration/inventory/test_unit_creation.py` |
| BBMS-F-021 | TC-Inv-02 | P | `tests/integration/inventory/test_unit_creation.py`, `test_input_security.py` |
| BBMS-F-022 | TC-Inv-03 | P | `tests/integration/inventory/test_stock_transitions.py`; SQLite concurrency case separately skipped |
| BBMS-F-023 | TC-Inv-04 | P | `tests/integration/inventory/test_inventory_search.py` |
| BBMS-F-024 | TC-Inv-05 | P | `tests/integration/inventory/test_expiry_job.py` |
| BBMS-F-030 | TC-Req-01 | P | `tests/integration/requests/test_request_submission.py` |
| BBMS-F-031 | TC-Req-02 | P | `tests/integration/requests/test_request_decisions.py` |
| BBMS-F-032 | TC-Req-03 | P | `tests/integration/requests/test_fulfillment.py`; SQLite concurrency case separately skipped |
| BBMS-F-033 | TC-Req-04 | P | `tests/integration/requests/test_request_history.py` |
| BBMS-F-034 | TC-Req-05 | P | Full 64-pair ABO/Rh matrix for each of four components, `tests/unit/requests/test_compatibility.py` |
| BBMS-F-040 | TC-Notif-01 | P | `tests/integration/notifications/test_notification_delivery.py` |
| BBMS-F-041 | TC-Notif-02 | P | `tests/integration/inventory/test_low_stock_alerts.py`; SQLite concurrency case separately skipped |
| BBMS-F-042 | TC-Report-01 | F | Admin inventory grouped-summary assertion fails due fixture timestamp; issue [#174](https://github.com/DukeAvi/SE_miniProject/issues/174). Other report assertions in the same suite pass before this assertion. |
| BBMS-F-050 | TC-Admin-01 | P | `tests/integration/adminops/test_staff_account_management.py` |
| BBMS-F-051 | TC-Audit-01 | P | `tests/integration/audit/` and account/security event tests |
| BBMS-NF-001 | TC-Perf-01 | NR | No representative load run and no verified 95th-percentile latency sample. |
| BBMS-NF-002 | TC-Reli-01 | NR | No measured monthly availability window or uptime evidence. |
| BBMS-NF-003 | TC-Sec-01 | P | Automated password-hashing and sensitive-logging tests passed; no independent security review claimed. |
| BBMS-NF-004 | TC-Audit-02 | Partial | PR #172 branch automated run passed 650 tests with 5 SQLite skips; PR remains unmerged. One-year boundary, controlled purge, and production-role/database boundary are not fully signed off by this baseline report. |
| BBMS-NF-005 | TC-UX-01 | Partial | Manual role/browser and responsive checks recorded in [TC-UX-01](../TC-UX-01.md); screen-reader, complete keyboard-only pass, and screenshot attachments remain outstanding. |
| BBMS-NF-006 | TC-DR-01 | Partial | Backup/restore code tests exist and ran in the suite; a separately witnessed restore with measured RPO/RTO is not attached to this execution. |
| BBMS-SR-001 | TC-Sec-01 | Partial | TLS settings/configuration tests passed; no external deployed-endpoint TLS 1.2+ inspection was performed. |
| BBMS-SR-002 | TC-Sec-02 | P | 84-cell role permission test passed. |
| BBMS-SR-003 | TC-Sec-03 | P | Automated input-validation/security tests passed; no independent comprehensive fuzzing campaign is claimed. |
| BBMS-SR-004 | TC-Sec-04 | P | Security event and audit tests passed in automated suite. |
| BBMS-SR-005 | TC-Sec-05 | P | Session timeout tests passed in automated suite. |

## Traceability notes

The SRS RTM marks every requirement `N` (not run), while the STP directs execution to update those statuses. This report records observed results here rather than editing the submitted source SRS. The test plan labels §5.1 as blood compatibility and §5.4 as security validation; the separate evaluator checklist appears to refer to §5.1 as security. Preserve the original compatibility tests and resolve this numbering conflict in the project source documents before final submission.

UAT and Product Owner approval are not recorded as completed. No `P` above substitutes for representative user acceptance or release sign-off.
