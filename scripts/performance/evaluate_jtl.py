"""Apply TC-Perf-01's p95 and request-success assertions to JMeter CSV output."""

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path


LABELS = ("Search inventory", "Dashboard donation report")
LIMIT_MS = 3000


def evaluate(source: Path, output: Path, warmup_seconds: int = 30) -> dict:
    with source.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("JMeter produced no samples.")
    first_time = min(int(row["timeStamp"]) for row in rows)
    selected = [
        row for row in rows
        if int(row["timeStamp"]) >= first_time + warmup_seconds * 1000
    ]
    results = {}
    failures = []
    for label in LABELS:
        samples = [row for row in selected if row["label"] == label]
        if not samples:
            raise ValueError(f"JMeter produced no measured samples for {label!r}.")
        elapsed = sorted(int(row["elapsed"]) for row in samples)
        p95 = elapsed[math.ceil(0.95 * len(elapsed)) - 1]
        unsuccessful = [row for row in samples if row.get("success", "").lower() != "true"]
        non_200 = [row for row in samples if row.get("responseCode") != "200"]
        results[label] = {
            "samples": len(samples),
            "p95_ms": p95,
            "limit_ms": LIMIT_MS,
            "failed_samples": len(unsuccessful),
            "non_200_responses": len(non_200),
            "passed": p95 <= LIMIT_MS and not unsuccessful and not non_200,
        }
        if not results[label]["passed"]:
            failures.append(label)

    report = {
        "test_case": "TC-Perf-01",
        "measurement": "first 300 seconds after the 30 second ramp/warm-up",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "flows": results,
        "passed": not failures,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for label, details in results.items():
        print(
            f"{label}: p95={details['p95_ms']}ms, "
            f"samples={details['samples']}, failures={details['failed_samples']}"
        )
    if failures:
        raise SystemExit("Performance criteria failed: " + ", ".join(failures))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--warmup-seconds", type=int, default=30)
    arguments = parser.parse_args()
    evaluate(arguments.input, arguments.output, arguments.warmup_seconds)
