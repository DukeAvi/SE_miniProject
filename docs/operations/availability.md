# Health and availability operations

Traceability: `BBMS-NF-002` / `DS-NF-002` / `TC-Reli-01` (GitHub issue #74).

## Readiness endpoint

`GET /healthz` executes a minimal `SELECT 1` against the configured primary database. It returns `200 {"status":"ok"}` when the database responds and `503 {"status":"unavailable"}` otherwise. The response omits connection details and exception text. It checks database readiness; it does not report Celery worker readiness.

## Application process supervision

`compose.yaml` defines health checks and `restart: unless-stopped` for the web, worker, and Beat containers. The Docker Engine restarts a container when its main process exits and starts those containers after a daemon/host restart. A health check reports an unhealthy container; it does not restart a process that remains alive but unhealthy. Deployments must monitor health status and investigate repeated unhealthy states.

Start the app services with:

```bash
docker compose up -d db redis web worker beat
```

## External monitoring and alert delivery

For an independent public probe, run the monitoring stack on a host outside the BBMS application host. Configure the following values in that host's untracked `.env` file:

- `BBMS_PUBLIC_HEALTH_URL`: the externally reachable `https://.../healthz` URL.
- `BBMS_ALERT_WEBHOOK_URL`: an HTTPS webhook destination that accepts a JSON `alerts` array.
- `BBMS_ALERT_WEBHOOK_BEARER_TOKEN`: optional bearer credential for that destination.
- `DJANGO_ALLOWED_HOSTS`: a comma-separated list that includes the public hostname; do not use `*`.

Never place live destinations or credentials in source control. Start only the monitoring services on the monitoring host:

```bash
docker compose -f compose.monitoring.yaml up -d
```

The configuration preflight rejects non-HTTPS URLs and URLs containing embedded credentials, then writes the public target to the shared file-discovery volume. Prometheus/Blackbox probe the public health URL every 60 seconds. Prometheus and Alertmanager web interfaces bind to loopback by default. Prometheus keeps 400 days of samples in the persistent `prometheus-data` volume. Back up that volume if the monitoring history must survive loss of the monitoring host.

The probe-failure rule fires after the third consecutive failed one-minute evaluation (`for: 2m`). The HTTP 5xx rule uses actual application request counts over five minutes and fires above one percent. Configure the authenticated app metrics scrape described in the performance guide. Alertmanager forwards sanitized alerts through the internal receiver and records delivery evidence. Failed delivery returns HTTP 502 for retry.

Prometheus rules are checked by `promtool` in CI, including a rule test covering the three-failure and five-minute 5xx thresholds. A production verification still needs to confirm public reachability, webhook acceptance, and delivery behavior from the deployed monitoring host.

## Maintenance and monthly availability

Record approved maintenance periods in UTC in `deployment/maintenance.json`. Use ISO-8601 timestamps with explicit `Z` or UTC offset. Windows are half-open: the start is excluded from service availability and the end is included again. Keep the manifest in the deployment release record alongside the monthly report.

Generate a report from retained Prometheus samples:

```bash
python manage.py availability_report --month YYYY-MM --prometheus-url http://localhost:9090
```

The JSON includes probe, excluded-maintenance, included, successful, and failed sample counts, the calculated percentage, the 99.5% target, and whether the target was met. The calculation is `successful included samples / all included samples * 100`. If Prometheus has no samples for the month, the command fails clearly rather than reporting 100%. If every sample falls in planned maintenance, the report emits a null percentage and `target_met: false`; zero observations do not demonstrate availability. Retain the report with the release evidence.
