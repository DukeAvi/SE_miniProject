"""Sanitized notification delivery health metrics for external monitors."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import Notification


FAILURE_RATE_WINDOW = timedelta(hours=1)


def notification_delivery_health(*, now=None):
    now = now or timezone.now()
    pending_count = Notification.objects.filter(status=Notification.Status.QUEUED).count()
    recent = Notification.objects.filter(
        last_attempt_at__gte=now - FAILURE_RATE_WINDOW
    )
    failed_count = recent.filter(status=Notification.Status.FAILED).count()
    completed_count = recent.filter(
        status__in=(Notification.Status.SENT, Notification.Status.FAILED)
    ).count()
    failure_rate_percent = (
        (failed_count / completed_count) * 100 if completed_count else 0.0
    )
    pending_threshold = settings.NOTIFICATION_PENDING_ALERT_THRESHOLD
    failure_threshold = settings.NOTIFICATION_FAILURE_RATE_ALERT_PERCENT
    alerts = []
    if pending_count >= pending_threshold:
        alerts.append("pending_count_threshold_exceeded")
    if completed_count and failure_rate_percent >= failure_threshold:
        alerts.append("failure_rate_threshold_exceeded")
    return not alerts, {
        "pending_count": pending_count,
        "pending_threshold": pending_threshold,
        "completed_count_last_hour": completed_count,
        "failed_count_last_hour": failed_count,
        "failure_rate_percent_last_hour": round(failure_rate_percent, 2),
        "failure_rate_threshold_percent": failure_threshold,
        "alerts": alerts,
    }
