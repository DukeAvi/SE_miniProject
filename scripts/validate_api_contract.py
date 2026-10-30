#!/usr/bin/env python3
"""Validate the OpenAPI/Postman contract and the routes already mounted by Django."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OPENAPI_PATH = ROOT / "docs" / "api" / "openapi.json"
POSTMAN_PATH = ROOT / "docs" / "api" / "BBMS-API-v1.postman_collection.json"


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    with OPENAPI_PATH.open(encoding="utf-8") as handle:
        spec = json.load(handle)
    with POSTMAN_PATH.open(encoding="utf-8") as handle:
        collection = json.load(handle)

    if spec.get("openapi") != "3.0.3":
        fail("OpenAPI version must be 3.0.3")
    paths = spec.get("paths", {})
    operations = {
        (method.upper(), path): operation
        for path, path_item in paths.items()
        for method, operation in path_item.items()
        if method in {"get", "post", "patch", "put", "delete"}
    }
    if not operations:
        fail("No OpenAPI operations found")

    schemas = spec.get("components", {}).get("schemas", {})

    def check_refs(value: object, location: str = "OpenAPI") -> None:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if reference:
                prefix = "#/components/schemas/"
                if not reference.startswith(prefix) or reference[len(prefix) :] not in schemas:
                    fail(f"Unresolved schema reference at {location}: {reference}")
            for key, child in value.items():
                check_refs(child, f"{location}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                check_refs(child, f"{location}[{index}]")

    check_refs(spec)

    error_schema = "#/components/schemas/ErrorEnvelope"
    unsafe_methods = {"POST", "PATCH", "PUT", "DELETE"}
    for (method, path), operation in operations.items():
        if not operation.get("operationId") or not operation.get("x-allowed-roles"):
            fail(f"Missing operationId or role restriction for {method} {path}")
        responses = operation.get("responses", {})
        if not responses:
            fail(f"Missing responses for {method} {path}")
        for status in ("400", "401", "403", "404", "409", "422", "429", "500", "503"):
            if responses.get(status, {}).get("content", {}).get("application/json", {}).get("schema", {}).get("$ref") != error_schema:
                fail(f"Missing standard error envelope for {method} {path} ({status})")
        success = next((value for code, value in responses.items() if code.isdigit() and int(code) < 300), None)
        if success and "content" in success and "example" not in success["content"].get("application/json", {}):
            fail(f"Missing success example for {method} {path}")
        if success and int(next(code for code, value in responses.items() if value is success)) != 204:
            if not success.get("content", {}).get("application/json", {}).get("schema"):
                fail(f"Missing success response schema for {method} {path}")
        request_content = operation.get("requestBody", {}).get("content", {}).get("application/json", {})
        if operation.get("requestBody") and (not request_content.get("schema") or "example" not in request_content):
            fail(f"Missing request schema or example for {method} {path}")

        is_public = "Public" in operation["x-allowed-roles"]
        security = operation.get("security", spec.get("security", []))
        required_schemes = set().union(*(set(item) for item in security)) if security else set()
        if method in unsafe_methods:
            if "CsrfHeader" not in required_schemes:
                fail(f"Missing CSRF security for {method} {path}")
            if not is_public and "SessionCookie" not in required_schemes:
                fail(f"Missing session security for {method} {path}")
        elif not is_public and "SessionCookie" not in required_schemes:
            fail(f"Missing session security for {method} {path}")

    issue_operation = operations.get(("POST", "/api/v1/requests/{id}/issue"))
    if not issue_operation or not any(
        p.get("name") == "Idempotency-Key" and p.get("required")
        for p in issue_operation.get("parameters", [])
    ):
        fail("The request issue operation must require Idempotency-Key")

    def flatten(items: list[dict]) -> list[dict]:
        flattened = []
        for item in items:
            if "request" in item:
                flattened.append(item)
            else:
                flattened.extend(flatten(item.get("item", [])))
        return flattened

    items = flatten(collection.get("item", []))
    postman_keys = set()
    for item in items:
        request = item.get("request", {})
        method = request.get("method", "").upper()
        raw_url = request.get("url", "")
        if isinstance(raw_url, dict):
            raw_url = raw_url.get("raw", "")
        raw_url = raw_url.replace("{{baseUrl}}", "https://contract.invalid")
        path = urlsplit(raw_url).path.replace("{{id}}", "{id}").replace("{{resource}}", "{resource}")
        postman_keys.add((method, path))
        expected_success = next((code for code in operations.get((method, path), {}).get("responses", {}) if code.isdigit() and int(code) < 300), None)
        tests = "\n".join(
            "\n".join(event.get("script", {}).get("exec", []))
            for event in item.get("event", [])
            if event.get("listen") == "test"
        )
        if expected_success and f"to.have.status({expected_success})" not in tests:
            fail(f"Missing expected-status assertion for Postman request: {item.get('name')}")
        if operations.get((method, path), {}).get("requestBody") and not request.get("body"):
            fail(f"Missing Postman request body for {method} {path}")
        if any(header.get("key", "").lower() == "cookie" for header in request.get("header", [])):
            fail(f"Do not commit session cookies in Postman request: {item.get('name')}")
    if postman_keys != set(operations):
        missing = sorted(set(operations) - postman_keys)
        extra = sorted(postman_keys - set(operations))
        fail(f"Postman/OpenAPI mismatch; missing={missing}, extra={extra}")

    variables = collection.get("variable", [])
    keys = [item.get("key") for item in variables]
    if len(keys) != len(set(keys)):
        fail("Duplicate Postman collection variables")
    for item in variables:
        if item.get("key") in {"csrfToken", "demoPassword", "demoEmail", "sessionId"} and item.get("value"):
            fail(f"Postman variable {item['key']} must be blank")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bbms.settings_test")
    import django

    django.setup()
    from django.urls import resolve

    implemented = [
        (method, path)
        for (method, path), operation in operations.items()
        if operation.get("x-implementation-status") == "implemented"
    ]
    for method, path in implemented:
        # Django's UUID path converter rejects the literal OpenAPI `{id}` marker.
        # Resolve a representative UUID while keeping the OpenAPI path as-is.
        resolvable_path = path.replace("{id}", "00000000-0000-4000-8000-000000000000")
        try:
            match = resolve(resolvable_path)
        except Exception as error:  # Django raises Resolver404 for an absent route.
            fail(f"Documented implemented route does not resolve: {method} {path}: {error}")
        view_class = getattr(match.func, "cls", None)
        if path == "/healthz":
            if method != "GET":
                fail("The health endpoint is GET only")
        elif view_class is None or not hasattr(view_class, method.lower()):
            fail(f"Documented method is not implemented by the resolved view: {method} {path}")

    print(f"Validated {len(operations)} OpenAPI operations and {len(items)} Postman requests.")
    print(f"Resolved {len(implemented)} operations currently implemented in Django.")


if __name__ == "__main__":
    main()
