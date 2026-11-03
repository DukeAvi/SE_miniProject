"""Asynchronous notification outbox delivery tasks."""

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Notification
from .services import MAX_DELIVERY_ATTEMPTS, RETRY_BACKOFF_SECONDS, due_notification_ids


logger = logging.getLogger(__name__)


@shared_task(name="apps.notifications.tasks.deliver_notification")
def deliver_notification(notification_id):
    """Deliver one queued event once, retaining sanitized failure state for retry."""
    now = timezone.now()
    with transaction.atomic():
        try:
            notification = Notification.objects.select_for_update().get(pk=notification_id)
        except Notification.DoesNotExist:
            return {"status": "missing"}
        if notification.status != Notification.Status.QUEUED:
            return {"status": notification.status.lower()}
        if notification.next_attempt_at and notification.next_attempt_at > now:
            return {"status": "not_due"}

        notification.attempt_count += 1
        notification.last_attempt_at = now
        try:
            from .services import get_notification_adapter

            get_notification_adapter().deliver(notification.type)
        except Exception:
            notification.sent_at = None
            if notification.attempt_count >= MAX_DELIVERY_ATTEMPTS:
                notification.status = Notification.Status.FAILED
                notification.next_attempt_at = None
                notification.failure_code = "DELIVERY_FAILED"
                logger.warning("Notification delivery failed after maximum attempts")
            else:
                delay = RETRY_BACKOFF_SECONDS[notification.attempt_count - 1]
                notification.next_attempt_at = now + timedelta(seconds=delay)
                logger.warning("Notification delivery failed; retry scheduled")
        else:
            notification.status = Notification.Status.SENT
            notification.sent_at = now
            notification.next_attempt_at = None
            notification.failure_code = ""

        notification.save(update_fields=(
            "status",
            "attempt_count",
            "next_attempt_at",
            "last_attempt_at",
            "sent_at",
            "failure_code",
        ))
        return {
            "status": notification.status.lower(),
            "attempt_count": notification.attempt_count,
        }


@shared_task(name="apps.notifications.tasks.dispatch_queued_notifications")
def dispatch_queued_notifications():
    """Sweep the outbox so retries survive worker or broker interruptions."""
    notification_ids = due_notification_ids()
    for notification_id in notification_ids:
        deliver_notification.apply_async(args=[str(notification_id)])
    return {"queued_count": len(notification_ids)}
