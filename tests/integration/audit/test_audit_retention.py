from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.db.utils import NotSupportedError

from apps.audit.models import AuditEvent
from apps.audit.services import run_retention, search_events


pytestmark = pytest.mark.django_db


def create_event_at(when, *, action=AuditEvent.Action.LOGIN_SUCCESS):
    with patch("django.utils.timezone.now", return_value=when):
        return AuditEvent.objects.create(action=action)


def test_retention_uses_one_year_utc_anniversary_and_keeps_boundary():
    now = datetime(2026, 11, 4, 12, tzinfo=UTC)
    cutoff = datetime(2025, 11, 4, 12, tzinfo=UTC)
    too_old = create_event_at(cutoff - timedelta(microseconds=1))
    at_boundary = create_event_at(cutoff)
    recent = create_event_at(cutoff + timedelta(microseconds=1))

    result = run_retention(now=now, dry_run=False)

    assert result["cutoff"] == cutoff
    assert result["eligible_count"] == 1
    assert result["deleted_count"] == 1
    assert not AuditEvent.objects.filter(pk=too_old.pk).exists()
    assert AuditEvent.objects.filter(pk=at_boundary.pk).exists()
    assert AuditEvent.objects.filter(pk=recent.pk).exists()
    assert list(
        search_events(action=AuditEvent.Action.LOGIN_SUCCESS, from_date=cutoff.date())
    ) == [recent, at_boundary]
    run_event = AuditEvent.objects.get(
        action=AuditEvent.Action.AUDIT_RETENTION_RUN,
        entity_id=str(result["run_id"]),
    )
    assert run_event.outcome == AuditEvent.Outcome.SUCCESS
    assert run_event.correlation_id == result["run_id"]


def test_retention_dry_run_records_run_without_deleting_eligible_rows():
    now = datetime(2026, 11, 4, 12, tzinfo=UTC)
    old = create_event_at(datetime(2025, 1, 1, tzinfo=UTC))

    result = run_retention(now=now)

    assert result["dry_run"] is True
    assert result["eligible_count"] == 1
    assert result["deleted_count"] == 0
    assert AuditEvent.objects.filter(pk=old.pk).exists()
    assert AuditEvent.objects.filter(
        action=AuditEvent.Action.AUDIT_RETENTION_DRY_RUN,
        entity_id=str(result["run_id"]),
        outcome=AuditEvent.Outcome.SUCCESS,
    ).exists()


def test_failed_purge_rolls_back_deletion_and_writes_failure_event(monkeypatch):
    now = datetime(2026, 11, 4, 12, tzinfo=UTC)
    old = create_event_at(datetime(2025, 1, 1, tzinfo=UTC))

    def fail_delete(self, using):
        raise RuntimeError("simulated delete failure")

    monkeypatch.setattr("django.db.models.query.QuerySet._raw_delete", fail_delete)
    with pytest.raises(RuntimeError, match="simulated delete failure"):
        run_retention(now=now, dry_run=False)

    assert AuditEvent.objects.filter(pk=old.pk).exists()
    failed = AuditEvent.objects.get(
        action=AuditEvent.Action.AUDIT_RETENTION_RUN,
        outcome=AuditEvent.Outcome.FAILURE,
    )
    assert failed.entity_type == "AUDIT_RETENTION_RUN"


def test_retention_rejects_naive_clock_values():
    with pytest.raises(ValidationError, match="timezone-aware"):
        run_retention(now=datetime(2026, 11, 4, 12), dry_run=True)


def test_one_year_cutoff_for_leap_day_clamps_to_february_28():
    result = run_retention(now=datetime(2024, 2, 29, 12, tzinfo=UTC))

    assert result["cutoff"] == datetime(2023, 2, 28, 12, tzinfo=UTC)


def test_ordinary_model_and_queryset_deletes_remain_blocked():
    event = create_event_at(datetime(2026, 11, 4, 12, tzinfo=UTC))

    with pytest.raises(ValidationError, match="append-only"):
        event.delete()
    with pytest.raises(NotSupportedError, match="append-only"):
        AuditEvent.objects.filter(pk=event.pk).delete()


def test_retention_command_defaults_to_dry_run_and_requires_execute(capsys):
    old = create_event_at(datetime(2025, 1, 1, tzinfo=UTC))

    call_command("purge_audit_events")
    output = capsys.readouterr().out
    assert "dry run" in output
    assert "eligible=1 deleted=0" in output
    assert AuditEvent.objects.filter(pk=old.pk).exists()

    call_command("purge_audit_events", "--execute")
    output = capsys.readouterr().out
    assert "purged" in output
    assert "eligible=1 deleted=1" in output
    assert not AuditEvent.objects.filter(pk=old.pk).exists()


def test_search_indexes_cover_audit_filter_dimensions():
    indexed = {tuple(index.fields) for index in AuditEvent._meta.indexes}

    assert ("occurred_at",) in indexed or AuditEvent._meta.get_field("occurred_at").db_index
    assert ("actor", "occurred_at") in indexed
    assert ("action", "occurred_at") in indexed
    assert ("entity_type", "entity_id", "occurred_at") in indexed
