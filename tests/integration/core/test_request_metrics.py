from django.test import Client, override_settings


@override_settings(PROMETHEUS_METRICS_BEARER_TOKEN="test-metrics-bearer-token-0123456789")
def test_metrics_expose_low_cardinality_request_latency_and_only_allow_get():
    client = Client()
    assert client.get("/api/v1/auth/csrf").status_code == 200
    assert client.get("/api/v1/auth/csrf?email=person%40example.test").status_code == 400

    assert client.get("/metrics").status_code == 403
    response = client.get(
        "/metrics",
        HTTP_AUTHORIZATION="Bearer test-metrics-bearer-token-0123456789",
    )

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
    body = response.content.decode()
    assert "bbms_http_request_duration_seconds_bucket" in body
    assert 'route="api/v1/auth/csrf"' in body
    assert "person@example.test" not in body
    assert 'status_code="400"' in body
    assert "request.path" not in body
    assert client.post(
        "/metrics",
        HTTP_AUTHORIZATION="Bearer test-metrics-bearer-token-0123456789",
    ).status_code == 405


def test_metrics_fail_closed_when_deployment_token_is_missing():
    response = Client().get("/metrics")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
