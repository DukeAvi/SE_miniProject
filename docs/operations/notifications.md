# Notification delivery operations

BBMS-F-040 / DS-040 / TC-Notif-01 implements asynchronous delivery from the durable notification outbox. Request approval, rejection, hold, reservation, and fulfillment create one outbox row per request and notification type inside the same transaction as the status change. Provider failures do not undo that user action.

## Runtime

Version 1.0 uses `NOTIFICATION_PROVIDER=console`; it makes no email or SMS calls and logs no recipient or clinical data. Automated tests inject the deterministic mock adapter. External providers require a separate approved decision and secret-management design.

Run Redis, one Celery worker, and one Beat scheduler using the `CELERY_BROKER_URL` configuration:

```text
celery -A bbms worker --loglevel=INFO
celery -A bbms beat --loglevel=INFO
```

New outbox rows are dispatched after their transaction commits. Beat also sweeps due `QUEUED` rows every minute, which recovers dispatches missed during broker or worker interruptions. Failed attempts retry after 60, 120, 240, and 480 seconds. After the fifth attempt, the row becomes `FAILED` with the sanitized `DELIVERY_FAILED` code and is visible to Admin at `/api/v1/admin/notification-failures`.

## Monitoring and recovery

Configure an independent process monitor to run this command at least every 5 minutes:

```text
python manage.py check_notification_delivery
```

It emits sanitized JSON and exits nonzero when queued notifications reach `NOTIFICATION_PENDING_ALERT_THRESHOLD` (default `100`) or the failed share of completed deliveries in the last hour reaches `NOTIFICATION_FAILURE_RATE_ALERT_PERCENT` (default `10`). Configure positive pending thresholds and a failure percentage from 1 to 100. The failure rate is zero when there are no completed deliveries in the window.

The Beat sweep safely requeues every due queued notification; no manual replay of a failed row is provided. Admin can review permanent failure codes and operators can address the delivery configuration before any future retry workflow is authorized.

## Data handling

The outbox stores only a request or stock-alert reference, recipient account reference, notification type, state, attempt timestamps/count, and sanitized failure code. It does not store message bodies, phone numbers, email addresses, provider responses, credentials, or tokens. User notification reads are scoped to the authenticated account.
