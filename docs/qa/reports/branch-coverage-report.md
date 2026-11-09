# Branch Coverage Report — Sprint 2 QA

**Revision:** `f693371ba0fce6d5d7d57e03ff2aa6dfff47d8f2` (`main`)
**Date:** 2026-11-05 (Asia/Kolkata)
**Scope:** Python modules under `apps/`; frontend code is not included.
**Tool:** Coverage.py 7.17.2 `--branch`.

The full pytest run executed 513 of 620 measured branches (82.74%), leaving 107 unexecuted. This aggregate does not imply each feature has complete decision coverage. The run ended with 639 passed, 1 failed, and 5 PostgreSQL-only concurrency/locking tests skipped on SQLite. See [Coverage Report](coverage-report.md) for the command and [QA-002 execution summary](QA-002-execution-summary.md) for the failure disposition.

The native coverage JSON is an ephemeral `/tmp` artifact, not a committed test database or user-data file. PostgreSQL execution, targeted missing-branch analysis, and frontend branch coverage have not been performed.
