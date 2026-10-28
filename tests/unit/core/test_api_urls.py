from django.urls import get_resolver


def test_api_v1_exposes_application_prefixes():
    root_patterns = get_resolver().url_patterns
    api = next(pattern for pattern in root_patterns if str(pattern.pattern) == "api/v1/")

    prefixes = {str(pattern.pattern) for pattern in api.url_patterns}

    assert prefixes == {
        "",
        "administration/",
        "audit/",
        "donors/",
        "inventory/",
        "notifications/",
        "requests/",
    }
