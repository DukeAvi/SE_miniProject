"""Run the PostgreSQL-backed TC-Perf-01 JMeter profile locally or in CI."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    results = Path(os.environ.get("PERF_RESULTS_DIR", "performance-results")).resolve()
    credentials_file = Path(os.environ.get("PERF_CREDENTIALS_FILE", ""))
    jmeter = Path(os.environ.get("JMETER_BIN", ""))
    if not credentials_file.is_file() or not jmeter.is_file():
        raise SystemExit("Set PERF_CREDENTIALS_FILE and JMETER_BIN to the benchmark inputs.")

    credentials = json.loads(credentials_file.read_text(encoding="utf-8"))
    results.mkdir(parents=True, exist_ok=True)
    multiprocess_dir = Path(os.environ.get("PROMETHEUS_MULTIPROC_DIR", results / "metrics"))
    multiprocess_dir.mkdir(parents=True, exist_ok=True)
    for entry in multiprocess_dir.iterdir():
        if entry.is_file():
            entry.unlink()

    server_environment = os.environ.copy()
    server_environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "bbms.settings",
            "DJANGO_DEBUG": "false",
            "DJANGO_ALLOWED_HOSTS": "127.0.0.1,localhost",
            "SECURE_SSL_REDIRECT": "false",
            "SESSION_COOKIE_SECURE": "false",
            "CSRF_COOKIE_SECURE": "false",
            "PROMETHEUS_METRICS_BEARER_TOKEN": (
                "benchmark-metrics-token-that-is-only-used-in-this-local-run"
            ),
            "PROMETHEUS_MULTIPROC_DIR": str(multiprocess_dir),
        }
    )
    server_log = (results / "gunicorn.log").open("wb")
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "gunicorn",
            "--config",
            "gunicorn.conf.py",
            "--bind",
            "127.0.0.1:8000",
            "--workers",
            "2",
            "bbms.wsgi:application",
        ],
        cwd=ROOT,
        env=server_environment,
        stdout=server_log,
        stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(60):
            if server.poll() is not None:
                raise RuntimeError("Gunicorn exited before becoming ready; see gunicorn.log.")
            try:
                with urlopen("http://127.0.0.1:8000/healthz", timeout=2) as response:
                    if response.status == 200:
                        break
            except (OSError, URLError):
                time.sleep(1)
        else:
            raise RuntimeError("Gunicorn did not become ready within 60 seconds.")

        jtl = results / "tc-perf-01.jtl"
        command = [
            str(jmeter), "-n", "-t", str(ROOT / "tests/performance/tc_perf_01.jmx"),
            "-Jhost=127.0.0.1", "-Jport=8000", "-Jemail=" + credentials["email"],
            "-Jpassword=" + credentials["password"],
            "-Jfrom=" + credentials["from_date"], "-Jto=" + credentials["to_date"],
            "-Jthreads=20", "-Jramp=30", "-Jduration=330",
            "-Jjmeter.save.saveservice.print_field_names=true",
            "-l", str(jtl), "-j", str(results / "jmeter.log"),
        ]
        subprocess.run(command, cwd=ROOT, check=True)
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/performance/evaluate_jtl.py"),
                "--input", str(jtl), "--output", str(results / "summary.json"),
            ],
            cwd=ROOT,
            check=True,
        )
        plans_environment = os.environ.copy()
        plans_environment.update(server_environment)
        plans_environment["PERF_QUERY_PLAN_FILE"] = str(results / "query-plans.json")
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/performance/capture_query_plans.py")],
            cwd=ROOT,
            env=plans_environment,
            check=True,
        )
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
        server_log.close()
        for entry in multiprocess_dir.iterdir():
            if entry.is_file():
                entry.unlink()


if __name__ == "__main__":
    main()
