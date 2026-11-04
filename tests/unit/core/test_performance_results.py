import csv

import pytest

from scripts.performance.evaluate_jtl import evaluate


def write_jtl(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("timeStamp", "elapsed", "label", "responseCode", "success"),
        )
        writer.writeheader()
        writer.writerows(rows)


def test_evaluator_excludes_warmup_and_checks_both_flow_p95(tmp_path):
    jtl = tmp_path / "results.jtl"
    rows = [
        {"timeStamp": "1000", "elapsed": "9000", "label": "Search inventory", "responseCode": "503", "success": "false"},
    ]
    for index in range(100):
        for label in ("Search inventory", "Dashboard donation report"):
            rows.append({
                "timeStamp": str(31_000 + index),
                "elapsed": str(100 + index),
                "label": label,
                "responseCode": "200",
                "success": "true",
            })
    write_jtl(jtl, rows)

    report = evaluate(jtl, tmp_path / "summary.json")

    assert report["passed"] is True
    assert report["flows"]["Search inventory"]["samples"] == 100
    assert report["flows"]["Dashboard donation report"]["p95_ms"] == 194


def test_evaluator_fails_a_flow_that_exceeds_three_seconds_or_has_http_errors(tmp_path):
    jtl = tmp_path / "results.jtl"
    rows = [
        {"timeStamp": str(40_000 + index), "elapsed": "3100", "label": "Search inventory", "responseCode": "200", "success": "true"}
        for index in range(20)
    ] + [
        {"timeStamp": str(40_000 + index), "elapsed": "100", "label": "Dashboard donation report", "responseCode": "403", "success": "true"}
        for index in range(20)
    ]
    write_jtl(jtl, rows)

    with pytest.raises(SystemExit, match="Performance criteria failed"):
        evaluate(jtl, tmp_path / "summary.json", warmup_seconds=0)


def test_evaluator_rejects_missing_flow_samples(tmp_path):
    jtl = tmp_path / "results.jtl"
    write_jtl(jtl, [
        {"timeStamp": "1000", "elapsed": "100", "label": "Search inventory", "responseCode": "200", "success": "true"}
    ])

    with pytest.raises(ValueError, match="no measured samples"):
        evaluate(jtl, tmp_path / "summary.json", warmup_seconds=0)
