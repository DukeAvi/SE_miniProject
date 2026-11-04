import gzip

from django.http import HttpResponse
from django.middleware.gzip import GZipMiddleware
from django.test import RequestFactory


def test_gzip_middleware_compresses_accepted_large_json_responses():
    payload = b'{"results":[' + b'{"status":"AVAILABLE","component":"RBC"},' * 100 + b'{}]}'
    request = RequestFactory().get("/api/v1/inventory/units", HTTP_ACCEPT_ENCODING="gzip")

    response = GZipMiddleware(
        lambda _: HttpResponse(payload, content_type="application/json")
    )(request)

    assert response["Content-Encoding"] == "gzip"
    assert "Accept-Encoding" in response["Vary"]
    assert gzip.decompress(response.content) == payload
    assert len(response.content) < len(payload)


def test_gzip_middleware_leaves_unaccepted_or_small_responses_unchanged():
    middleware = GZipMiddleware(lambda _: HttpResponse("ok"))
    plain_request = RequestFactory().get("/healthz")
    small_gzip_request = RequestFactory().get("/healthz", HTTP_ACCEPT_ENCODING="gzip")

    assert "Content-Encoding" not in middleware(plain_request)
    assert "Content-Encoding" not in middleware(small_gzip_request)
