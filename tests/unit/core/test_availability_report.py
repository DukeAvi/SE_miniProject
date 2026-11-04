import json
from urllib.parse import parse_qs, urlparse

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.core.management.commands import availability_report


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_monthly_report_combines_probe_series_and_calculates_target(tmp_path, monkeypatch):
    maintenance = tmp_path / "maintenance.json"
    maintenance.write_text('{"windows": []}', encoding="utf-8")
    payload = {
        "status": "success",
        "data": {
            "result": [
                {"values": [["1793491200", "1"], ["1793491260", "0"]]},
                {"values": [["1793491320", "1"]]},
            ]
        },
    }
    requested = {}

    def fake_urlopen(url, **kwargs):
        requested["url"] = url
        return FakeResponse(payload)

    monkeypatch.setattr(availability_report, "urlopen", fake_urlopen)

    from io import StringIO

    output = StringIO()
    call_command(
        "availability_report",
        "--month=2026-11",
        "--prometheus-url=https://prometheus.example.test",
        f"--maintenance-file={maintenance}",
        stdout=output,
    )

    report = json.loads(output.getvalue())
    assert report["month"] == "2026-11"
    assert report["probe_samples"] == 3
    assert report["successful_samples"] == 2
    assert report["failed_samples"] == 1
    assert report["availability_percent"] == pytest.approx(66.6667)
    assert report["target_met"] is False
    assert report["expected_samples"] == 43200
    assert report["missing_samples"] == 43197
    assert report["coverage_complete"] is False
    query = parse_qs(urlparse(requested["url"]).query)
    assert query["start"] == ["2026-11-01T00:00:00+00:00"]
    assert query["end"] == ["2026-11-30T23:59:00+00:00"]


def test_monthly_report_rejects_an_empty_prometheus_range(tmp_path, monkeypatch):
    maintenance = tmp_path / "maintenance.json"
    maintenance.write_text('{"windows": []}', encoding="utf-8")
    payload = {"status": "success", "data": {"result": []}}
    monkeypatch.setattr(availability_report, "urlopen", lambda *args, **kwargs: FakeResponse(payload))

    with pytest.raises(CommandError, match="No health-probe samples"):
        call_command(
            "availability_report",
            "--month=2026-11",
            "--prometheus-url=https://prometheus.example.test",
            f"--maintenance-file={maintenance}",
        )


def test_monthly_report_rejects_maintenance_without_timezone(tmp_path):
    maintenance = tmp_path / "maintenance.json"
    maintenance.write_text(json.dumps({"windows": [{
        "start": "2026-11-01T00:00:00", "end": "2026-11-01T01:00:00",
    }]}), encoding="utf-8")
    with pytest.raises(CommandError, match="could not be read"):
        call_command("availability_report", "--month=2026-11", f"--maintenance-file={maintenance}")


def test_monthly_report_does_not_call_maintenance_only_month_100_percent(tmp_path, monkeypatch):
    maintenance = tmp_path / "maintenance.json"
    maintenance.write_text(
        '{"windows": [{"start": "2026-11-01T00:00:00Z", "end": "2026-12-01T00:00:00Z"}]}',
        encoding="utf-8",
    )
    payload = {
        "status": "success",
        "data": {"result": [{"values": [["1793491200", "1"]]}]},
    }
    monkeypatch.setattr(availability_report, "urlopen", lambda *args, **kwargs: FakeResponse(payload))

    from io import StringIO

    output = StringIO()
    call_command(
        "availability_report",
        "--month=2026-11",
        "--prometheus-url=https://prometheus.example.test",
        f"--maintenance-file={maintenance}",
        stdout=output,
    )

    report = json.loads(output.getvalue())
    assert report["included_samples"] == 0
    assert report["availability_percent"] is None
    assert report["target_met"] is False
