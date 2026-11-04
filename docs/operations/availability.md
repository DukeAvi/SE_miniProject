# Health and availability operations

## Readiness endpoint

`GET /healthz` executes a minimal `SELECT 1` against the configured primary database. It returns `200 {"status":"ok"}` when that dependency responds, or `503 {"status":"unavailable"}` when it does not. The response omits connection details and exception text. The endpoint is a database readiness check; it does not report Celery worker or broker readiness.

## Local supervised stack and monitoring

`compose.yaml` runs PostgreSQL, Redis, Django, Celery worker and Beat, Blackbox Exporter, Prometheus, Alertmanager, and a small webhook receiver. Services use restart policies and health checks. Set `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` before starting the stack; configure the receiver's external webhook destination in the deployment environment when needed.

Prometheus probes `/healthz` once per minute. Alerts fire after three consecutive failed probes or when the five-minute server-error rate exceeds one percent. Alert payloads are reduced to alert name, status, and timestamps before they are stored. Prometheus retains probe data for 400 days.

Record planned UTC maintenance windows in `deployment/maintenance.json`. Generate a monthly report with:

```bash
python manage.py availability_report --month YYYY-MM
```

The report excludes samples inside those maintenance windows and reports whether availability met the 99.5% target. For deployment evidence, retain the report and the Prometheus/Alertmanager firing history alongside the release record.
