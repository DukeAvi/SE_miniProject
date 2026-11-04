"""Fail fast when required public monitoring destinations are invalid."""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from scripts.alert_receiver import validate_https_url


def main():
    try:
        public_health_url = validate_https_url(
            os.environ.get("BBMS_PUBLIC_HEALTH_URL"),
            setting_name="BBMS_PUBLIC_HEALTH_URL",
        )
        validate_https_url(os.environ.get("BBMS_ALERT_WEBHOOK_URL"))
        target_file = Path(os.environ.get(
            "BBMS_PROBE_TARGET_FILE",
            "/etc/prometheus/targets/bbms-health.json",
        ))
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(
            json.dumps([{"targets": [public_health_url]}]) + "\n",
            encoding="utf-8",
        )
        metrics_target_file = Path(os.environ.get(
            "BBMS_METRICS_TARGET_FILE",
            "/etc/prometheus/targets/bbms-app-metrics.json",
        ))
        metrics_url = os.environ.get("BBMS_APP_METRICS_URL", "").strip()
        metrics_token = os.environ.get("BBMS_APP_METRICS_BEARER_TOKEN", "")
        metrics_targets = []
        if metrics_url:
            parsed = urlsplit(metrics_url)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path != "/metrics"
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("BBMS_APP_METRICS_URL must use HTTPS and end in /metrics")
            if len(metrics_token) < 32 or "\n" in metrics_token or "\r" in metrics_token:
                raise ValueError("BBMS_APP_METRICS_BEARER_TOKEN must contain at least 32 characters")
            default_port = 443
            address = parsed.hostname
            if parsed.port and parsed.port != default_port:
                address = f"{address}:{parsed.port}"
            metrics_targets.append({
                "targets": [address],
                "labels": {
                    "__scheme__": parsed.scheme,
                    "__metrics_path__": "/metrics",
                },
            })
        metrics_target_file.parent.mkdir(parents=True, exist_ok=True)
        metrics_target_file.write_text(json.dumps(metrics_targets) + "\n", encoding="utf-8")
        if metrics_url:
            token_file = metrics_target_file.parent / "bbms-app-metrics-token"
            token_file.write_text(metrics_token + "\n", encoding="utf-8")
            token_file.chmod(0o644)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError:
        print("Unable to write the monitoring target configuration.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
