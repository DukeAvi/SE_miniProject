import pytest
from django.test import Client, override_settings

from bbms.settings import postgres_ssl_options


@pytest.mark.parametrize(
    ("mode", "root_certificate", "expected"),
    [
        ("disable", "", {"sslmode": "disable"}),
        (
            "verify-full",
            "/run/secrets/postgres-ca.crt",
            {"sslmode": "verify-full", "sslrootcert": "/run/secrets/postgres-ca.crt"},
        ),
    ],
)
def test_postgres_ssl_options_are_explicit(mode, root_certificate, expected):
    assert postgres_ssl_options(mode, root_certificate) == expected


@pytest.mark.parametrize("mode", ["verify-ca", "verify-full"])
def test_postgres_certificate_verification_requires_a_trust_root(mode):
    with pytest.raises(ValueError, match="POSTGRES_SSLROOTCERT"):
        postgres_ssl_options(mode)


@pytest.mark.parametrize("mode", ["allow", "prefer", "require"])
def test_postgres_ssl_options_reject_modes_that_do_not_verify_database_identity(mode):
    with pytest.raises(ValueError, match="POSTGRES_SSLMODE"):
        postgres_ssl_options(mode)


def test_postgres_ssl_options_reject_unknown_modes():
    with pytest.raises(ValueError, match="POSTGRES_SSLMODE"):
        postgres_ssl_options("legacy-plaintext")


@override_settings(SECURE_SSL_REDIRECT=True, SECURE_HSTS_SECONDS=31536000)
@pytest.mark.django_db
def test_http_is_redirected_and_https_response_has_security_headers():
    client = Client()
    redirected = client.get("/healthz")
    assert redirected.status_code == 301
    assert redirected["Location"] == "https://testserver/healthz"

    response = client.get("/healthz", secure=True)
    assert response.status_code == 200
    assert response["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response["Content-Security-Policy"]


@override_settings(
    SECURE_SSL_REDIRECT=True,
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
)
@pytest.mark.django_db
def test_trusted_tls_proxy_header_is_required_for_secure_application_requests():
    client = Client()
    response = client.get("/healthz", HTTP_X_FORWARDED_PROTO="https")
    assert response.status_code == 200

    insecure = client.get("/healthz", HTTP_X_FORWARDED_PROTO="http")
    assert insecure.status_code == 301
    assert insecure["Location"] == "https://testserver/healthz"
