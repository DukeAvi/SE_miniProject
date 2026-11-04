# Performance target operations

Traceability: `BBMS-NF-001` / `DS-NF-001` / `TC-Perf-01` (GitHub issue #73).

## Instrumentation and alerting

The Django middleware records `bbms_http_request_duration_seconds` as a Prometheus histogram with resolved route template, HTTP method, and status code labels. It never labels metrics with request IDs, account identifiers, query strings, or user-supplied values. The `/metrics` endpoint is GET-only and requires the configured bearer token. Configure `BBMS_APP_METRICS_BEARER_TOKEN` with a random value of at least 32 characters in the app and monitoring deployment `.env` files. Keep `BBMS_APP_METRICS_URL` on a private HTTPS route and restrict it to the monitoring host at the network edge. The endpoint fails closed when its token is missing.

`GZipMiddleware` compresses responses over 200 bytes when clients advertise gzip and the compressed body is smaller; it sets `Vary: Accept-Encoding` and uses Django's randomized gzip header padding. Small and streaming responses are not buffered solely for compression.

For Gunicorn multi-worker deployments, `PROMETHEUS_MULTIPROC_DIR` points to a per-container tmpfs directory. The startup command clears that ephemeral directory before workers start; the Gunicorn `child_exit` hook retires dead-worker gauge files. Prometheus scrapes this endpoint every 15 seconds. `BbmsSearchDashboardP95LatencyAboveThreeSeconds` fires when the rolling five-minute p95 for inventory search or dashboard donation reports exceeds three seconds continuously for five minutes. `promtool test rules` covers the alert's pending and firing states.

## Reproducible normal-load profile

TC-Perf-01 uses an isolated PostgreSQL 16 database, Python 3.12, Django's production settings, and the same two-worker Gunicorn process count as the Compose web service. CI disables only HTTPS redirection and secure-cookie flags for its loopback HTTP test transport. It seeds 10,000 synthetic completed donations and 10,000 synthetic inventory units across 100 synthetic donor profiles. All accounts use `example.test`; no real or clinical data is used. Apache JMeter 5.6.3 starts 20 authenticated virtual users over a 30-second ramp, runs for 330 seconds, and uses a 250 ms think time between search and report requests. The first 30 seconds are excluded as warm-up; the remaining five minutes form the measurement window. Each iteration requests a 100-row inventory search and a 30-day donation dashboard report. The acceptance threshold is p95 <= 3,000 ms for each flow, with zero failed or non-200 samples.

The sprint review adopts this 20-user synthetic profile for the classroom project under the repository owner's delegated instruction to resolve the remaining review decisions. It measures project acceptance on the documented CI environment; production capacity requires separate measurement.

## Run locally

Use a clean, isolated PostgreSQL database. Do not run the seed against a production or shared database.

```bash
python -m pip install -r requirements-dev.txt
python manage.py migrate --noinput
PERF_BENCHMARK_CONFIRM=yes PERF_CREDENTIALS_FILE=/tmp/perf-credentials.json python scripts/performance/seed_dataset.py --credentials-file /tmp/perf-credentials.json
JMETER_BIN=/opt/apache-jmeter-5.6.3/bin/jmeter PERF_CREDENTIALS_FILE=/tmp/perf-credentials.json PERF_RESULTS_DIR=/tmp/bbms-performance python scripts/performance/run_benchmark.py
```

The run creates `tc-perf-01.jtl`, `summary.json`, `query-plans.json`, `jmeter.log`, and `gunicorn.log` in the selected results directory. The query plans use the real search and donation date-range ORM queries with PostgreSQL `EXPLAIN ANALYZE`. The CI workflow uploads the raw JTL and sanitized query-plan/report files as a run artifact for 14 days.

## Results

GitHub Actions run [41807600683](https://github.com/DukeAvi/SE_miniProject/actions/runs/41807600683) completed TC-Perf-01 against PostgreSQL 16 on 2026-11-04. Its uploaded artifact, `tc-perf-01-41807600683`, contains the raw JMeter JTL, summary, sanitized query plans, and service logs. The profile passed:

| Flow | Samples | p95 | Limit | Failed | Non-200 | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Inventory search | 11,392 | 18 ms | 3,000 ms | 0 | 0 | Pass |
| Dashboard donation report | 11,390 | 16 ms | 3,000 ms | 0 | 0 | Pass |

PostgreSQL `EXPLAIN ANALYZE` on the seeded test data showed the inventory search using `inv_search_filter_order_idx` with 100 returned rows and 0.230 ms execution time. The dashboard donation date-range query used `donation_date_pk_idx`, returned 100 rows, and took 0.177 ms. These are warm CI-run measurements on synthetic data, not production capacity claims. The run's full validation job failed afterward in `promtool test rules`: the new p95 alert test incorrectly expected a `job` label even though the rule's `sum by (le, route)` expression deliberately aggregates that label away. The test expectation now matches the actual alert labels; the next CI run must confirm the corrected rule test.

Retain a fresh artifact with each performance-affecting change. The latest PR revision must pass the complete CI job before merging; the earlier failed run above is retained as defect and rerun history.
