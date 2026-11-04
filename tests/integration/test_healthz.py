import pytest
from django.db import OperationalError, connection
from django.urls import reverse


pytestmark = pytest.mark.django_db


def test_healthz(client):
    response = client.get(reverse("healthz"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_reports_database_unavailable_without_exposing_error(client, monkeypatch):
    def unavailable_cursor(*args, **kwargs):
        raise OperationalError("private-database-host:5432")

    monkeypatch.setattr(connection, "cursor", unavailable_cursor)

    response = client.get(reverse("healthz"))

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert b"private-database-host" not in response.content


def test_healthz_only_accepts_get(client):
    response = client.post(reverse("healthz"))

    assert response.status_code == 405
