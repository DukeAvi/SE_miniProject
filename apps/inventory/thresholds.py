"""Low-stock threshold configuration and crossing evaluation."""

from django.db import transaction
from django.db.models import Sum

from apps.accounts.models import AccountRole, User
from apps.audit.services import record_event
from apps.notifications.models import Notification

from .models import BloodUnit, LowStockAlert, StockThreshold


class StockThresholdRejected(Exception):
    def __init__(self, code, message, *, status_code, details=None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def threshold_entity_id(blood_group, component):
    group_code = blood_group.replace("+", "POS").replace("-", "NEG")
    return f"{group_code}_{component}"


def get_stock_thresholds():
    return StockThreshold.objects.order_by("blood_group", "component")


def update_stock_thresholds(*, actor, thresholds, ip_address=None, as_of_date):
    """Update selected thresholds and audit/evaluate each key atomically."""
    if (
        not actor.is_authenticated
        or not actor.is_active
        or actor.role != AccountRole.ADMIN
    ):
        raise StockThresholdRejected(
            "forbidden", "Only Admin can change stock thresholds.", status_code=403
        )

    updated = []
    with transaction.atomic():
        for item in sorted(thresholds, key=lambda value: (value["blood_group"], value["component"])):
            threshold = StockThreshold.objects.select_for_update().get(
                blood_group=item["blood_group"],
                component=item["component"],
            )
            new_value = item["threshold_units"]
            raised_threshold = new_value > threshold.threshold_units
            if threshold.threshold_units != new_value:
                threshold.threshold_units = new_value
                threshold.save(update_fields=("threshold_units", "updated_at"))
                record_event(
                    action="THRESHOLD_CHANGED",
                    actor=actor,
                    entity_type="STOCK_THRESHOLD",
                    entity_id=threshold_entity_id(
                        threshold.blood_group, threshold.component
                    ),
                    ip_address=ip_address,
                )
            evaluate_stock_threshold(
                blood_group=threshold.blood_group,
                component=threshold.component,
                as_of_date=as_of_date,
                allow_alert=raised_threshold,
            )
            updated.append(threshold)
    return updated


def evaluate_stock_threshold(*, blood_group, component, as_of_date, allow_alert=True):
    """Create one alert on a downward crossing; clear suppression on recovery."""
    with transaction.atomic():
        threshold = StockThreshold.objects.select_for_update().get(
            blood_group=blood_group,
            component=component,
        )
        available_units = (
            BloodUnit.objects.filter(
                blood_group=blood_group,
                component=component,
                status=BloodUnit.Status.AVAILABLE,
                expiry_date__gt=as_of_date,
            ).aggregate(total=Sum("quantity_units"))["total"]
            or 0
        )

        if available_units < threshold.threshold_units:
            if threshold.alert_active or not allow_alert:
                return None
            alert = LowStockAlert.objects.create(
                threshold=threshold,
                available_units=available_units,
                threshold_units=threshold.threshold_units,
            )
            threshold.alert_active = True
            threshold.save(update_fields=("alert_active", "updated_at"))
            for recipient in User.objects.filter(
                role=AccountRole.STAFF,
                is_active=True,
            ).order_by("pk"):
                Notification.objects.create(
                    recipient=recipient,
                    stock_alert=alert,
                    type=Notification.Type.LOW_STOCK_ALERT,
                )
            record_event(
                action="LOW_STOCK_ALERTED",
                actor=None,
                entity_type="STOCK_THRESHOLD",
                entity_id=threshold_entity_id(blood_group, component),
            )
            return alert

        if threshold.alert_active:
            threshold.alert_active = False
            threshold.save(update_fields=("alert_active", "updated_at"))
        return None
