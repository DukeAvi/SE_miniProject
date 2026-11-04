# Health and availability operations

## Readiness endpoint

`GET /healthz` executes a minimal `SELECT 1` against the configured primary database. It returns `200 {"status":"ok"}` when that dependency responds, or `503 {"status":"unavailable"}` when it does not. The response omits connection details and exception text. The endpoint is a database readiness check; it does not report Celery worker or broker readiness.

## Deployment work still required for BBMS-NF-002 (#74)

The repository does not define a deployment target, packaged web/worker process units, external probe provider, public health URL, alert destination, or durable uptime/maintenance data source. As a result, this code change does not claim to configure process restart, a one-minute external probe, the three-failure/five-minute 5xx alerts, or the monthly 99.5% availability report.

Before those operational criteria can be implemented and verified, the repository owner must identify:

- The deployment target and how web, Celery worker, and Beat processes are supervised.
- The externally reachable probe URL and monitoring/alert destination.
- Where planned maintenance windows and probe results are recorded for monthly availability calculations.

The remaining operational work must include evidence of automatic restart, alert threshold behavior, maintenance exclusion, and the monthly availability calculation. Keep issue #74 open until that evidence exists.
