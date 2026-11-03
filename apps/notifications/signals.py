"""Dispatch committed outbox rows to the asynchronous worker."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification
from .services import dispatch_notification


@receiver(post_save, sender=Notification, dispatch_uid="notifications.enqueue_delivery")
def enqueue_notification_delivery(sender, instance, created, **kwargs):
    if created:
        dispatch_notification(str(instance.pk))
