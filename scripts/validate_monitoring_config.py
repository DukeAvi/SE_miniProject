"""Fail fast when required public monitoring destinations are invalid."""

import json
import os
import sys
from pathlib import Path

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
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError:
        print("Unable to write the public probe target configuration.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
