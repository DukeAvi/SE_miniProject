import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from scripts import alert_receiver


def test_webhook_must_be_https_and_must_not_embed_credentials():
    with pytest.raises(ValueError, match="HTTPS"):
        alert_receiver.validate_https_url("http://alerts.example.test/hook")
    with pytest.raises(ValueError, match="HTTPS"):
        alert_receiver.validate_https_url("https://user:password@alerts.example.test/hook")


def test_forwarder_sends_only_sanitized_fields_and_uses_bearer_auth():
    request_payload = alert_receiver.sanitize_payload({
        "alerts": [{
            "status": "firing",
            "labels": {"alertname": "DatabaseDown", "severity": "critical", "email": "patient@example.test"},
            "annotations": {"summary": "Database unavailable", "password": "do-not-forward"},
            "startsAt": "2026-11-01T00:00:00Z",
        }],
        "commonLabels": {"token": "do-not-forward"},
    })
    captured = {}

    class Response:
        status = 202

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def opener(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    alert_receiver.forward_alerts(
        request_payload,
        "https://alerts.example.test/hook",
        "bearer-secret",
        opener=opener,
    )

    sent = captured["request"].data.decode("utf-8")
    assert captured["request"].get_method() == "POST"
    assert captured["request"].get_header("Authorization") == "Bearer bearer-secret"
    assert captured["timeout"] == 10
    assert "patient@example.test" not in sent
    assert "do-not-forward" not in sent
    assert "Database unavailable" in sent


def test_alert_endpoint_forwards_and_persists_only_sanitized_evidence(tmp_path, monkeypatch):
    evidence = tmp_path / "alerts.jsonl"
    forwarded = []
    monkeypatch.setattr(alert_receiver, "forward_alerts", lambda payload, *args: forwarded.append(payload))
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        alert_receiver.make_handler("https://alerts.example.test/hook", "token", evidence),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/healthz", timeout=2) as response:
            assert response.status == 200

        body = json.dumps({
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "ProbeFailed", "severity": "critical", "account": "private"},
                "annotations": {"summary": "Public endpoint failed", "detail": "private detail"},
                "startsAt": "2026-11-01T00:00:00Z",
            }]
        }).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{server.server_port}/alerts",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            assert response.status == 204

        assert len(forwarded) == 1
        evidence_text = evidence.read_text(encoding="utf-8")
        assert "ProbeFailed" in evidence_text
        assert "private" not in evidence_text
        assert "private detail" not in evidence_text
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_alert_endpoint_returns_retryable_error_when_external_delivery_fails(tmp_path, monkeypatch):
    def fail_delivery(*args):
        raise URLError("private webhook token")

    monkeypatch.setattr(alert_receiver, "forward_alerts", fail_delivery)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        alert_receiver.make_handler("https://alerts.example.test/hook", "secret", tmp_path / "alerts.jsonl"),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/alerts",
            data=b'{"alerts": [{"labels": {"alertname": "ProbeFailed"}}]}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as error:
            urlopen(request, timeout=2)
        assert error.value.code == 502
        assert b"private webhook token" not in error.value.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_forwarder_propagates_delivery_failure_for_alertmanager_retry():
    def opener(*args, **kwargs):
        raise URLError("private destination response")

    with pytest.raises(URLError):
        alert_receiver.forward_alerts(
            {"alerts": []},
            "https://alerts.example.test/hook",
            opener=opener,
        )
