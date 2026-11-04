import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def test_compose_supervises_application_processes_and_requires_public_destinations():
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    services = compose["services"]

    for name in ("web", "worker", "beat", "alert-receiver"):
        assert services[name]["restart"] == "unless-stopped"
        assert services[name].get("healthcheck")

    assert "BBMS_PUBLIC_HEALTH_URL" in services["monitoring-config-check"]["environment"]
    assert "DJANGO_ALLOWED_HOSTS" in services["web"]["environment"]
    assert "probe-targets:/etc/prometheus/targets:ro" in services["prometheus"]["volumes"]
    assert "probe-targets:/app/var/probe-targets" in services["monitoring-config-check"]["volumes"]
    assert "alert-evidence:/app/var/alerts" in services["alert-receiver"]["volumes"]
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "/app/var/alerts /app/var/probe-targets" in dockerfile
    receiver_environment = services["alert-receiver"]["environment"]
    assert "BBMS_ALERT_WEBHOOK_URL" in receiver_environment
    assert "BBMS_ALERT_WEBHOOK_BEARER_TOKEN" in receiver_environment

    external_monitoring = yaml.safe_load(
        (ROOT / "compose.monitoring.yaml").read_text(encoding="utf-8")
    )
    assert set(external_monitoring["services"]) == {
        "blackbox", "monitoring-config-check", "prometheus", "alertmanager", "alert-receiver"
    }
    assert external_monitoring["services"]["prometheus"]["ports"] == ["127.0.0.1:9090:9090"]
    assert external_monitoring["services"]["alertmanager"]["ports"] == ["127.0.0.1:9093:9093"]
    assert "alert-evidence:/app/var/alerts" in external_monitoring["services"]["alert-receiver"]["volumes"]


def test_prometheus_probes_public_https_target_every_minute_and_retains_history():
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    config = yaml.safe_load((ROOT / "deployment/prometheus.yml").read_text(encoding="utf-8"))
    file_discovery = config["scrape_configs"][0]["file_sd_configs"][0]

    assert file_discovery["files"] == ["/etc/prometheus/targets/bbms-health.json"]
    assert file_discovery["refresh_interval"] == "1m"
    assert config["storage"]["tsdb"]["retention"]["time"] == "400d"
    assert "prometheus-data" in compose["services"]["prometheus"]["volumes"][-1]
    assert "prometheus-data" in compose["volumes"]


def test_alert_rules_use_required_probe_and_server_error_thresholds():
    config = yaml.safe_load((ROOT / "deployment/prometheus.yml").read_text(encoding="utf-8"))
    rules = yaml.safe_load((ROOT / "deployment/alerts.yml").read_text(encoding="utf-8"))
    alertmanager = yaml.safe_load((ROOT / "deployment/alertmanager.yml").read_text(encoding="utf-8"))
    assert config["global"]["scrape_interval"] == "60s"

    by_name = {rule["alert"]: rule for rule in rules["groups"][0]["rules"]}
    probe_failure = by_name["BbmsThreeConsecutiveProbeFailures"]
    assert probe_failure["expr"] == 'probe_success{job="bbms-health"} == 0'
    assert probe_failure["for"] == "2m"
    server_error = by_name["BbmsFiveMinute5xxRateAboveOnePercent"]
    assert "probe_http_status_code" in server_error["expr"]
    assert "[5m:1m]" in server_error["expr"]
    assert "> 0.01" in server_error["expr"]
    assert alertmanager["route"]["receiver"] == "bbms-alert-evidence"
    assert alertmanager["receivers"][0]["webhook_configs"][0]["url"] == (
        "http://alert-receiver:9095/alerts"
    )


def test_maintenance_window_manifest_is_valid_and_empty_by_default():
    manifest = json.loads((ROOT / "deployment/maintenance.json").read_text(encoding="utf-8"))
    assert manifest == {"windows": []}


def test_runtime_preflight_requires_https_urls_and_writes_public_target(tmp_path, monkeypatch):
    from scripts import validate_monitoring_config

    monkeypatch.setenv("BBMS_PUBLIC_HEALTH_URL", "http://bbms.example.test/healthz")
    monkeypatch.setenv("BBMS_ALERT_WEBHOOK_URL", "https://alerts.example.test/hook")
    monkeypatch.setenv("BBMS_PROBE_TARGET_FILE", str(tmp_path / "targets.json"))
    assert validate_monitoring_config.main() == 2

    monkeypatch.setenv("BBMS_PUBLIC_HEALTH_URL", "https://bbms.example.test/healthz")
    monkeypatch.setenv("BBMS_ALERT_WEBHOOK_URL", "https://alerts.example.test/hook")
    assert validate_monitoring_config.main() == 0
    targets = json.loads((tmp_path / "targets.json").read_text(encoding="utf-8"))
    assert targets == [{"targets": ["https://bbms.example.test/healthz"]}]
