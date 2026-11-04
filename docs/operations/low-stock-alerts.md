# Low-stock alert operations

BBMS-F-041 / DS-041 / TC-Notif-02 tracks thresholds by blood group and component. The migration seeds all supported pairs with `DEFAULT_STOCK_THRESHOLD` (default `5`); Admin can update one or more pairs through `GET` and `PUT /api/v1/admin/stock-thresholds`. Threshold values must be positive integers. Unspecified pairs keep their current value.

## Evaluation behavior

The stock measure is the sum of `quantity_units` for unexpired units in `AVAILABLE` state, using the configured blood-bank date boundary. Every inventory state transition reevaluates its pair inside the same transaction, including reservation, release, issue, discard, return, and expiry. Verified unit creation reevaluates the pair as stock recovers. The scheduled daily expiry job uses the same transition service, so expiry cannot bypass evaluation.

When available quantity moves below its threshold and `alert_active` is false, the system records a `LowStockAlert`, marks the threshold active, records `LOW_STOCK_ALERTED`, and creates one LOW_STOCK_ALERT outbox notification per active Staff account in one transaction. A unique database constraint prevents duplicate notification rows for the same Staff account and alert. Further checks while below threshold do not create another alert. When quantity reaches or exceeds the threshold, `alert_active` clears; a future downward crossing creates a new alert.

Changing a threshold is audited as `THRESHOLD_CHANGED` only when its value changes. The pair is reevaluated in the same transaction, so raising a threshold can trigger an alert and lowering one can clear an active alert if stock meets the new value.

## Access and recovery

Only Admin can view or change thresholds. Staff receive alerts through their own notification list at `/api/v1/notifications`; other users cannot read Staff notifications. Use `/api/v1/admin/audit-logs` to review threshold changes and alert events. A failed database transaction leaves the stock transition, threshold state, audit event, alert, and outbox rows rolled back together.
