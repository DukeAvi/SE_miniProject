from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("audit", "0006_audit_retention_actions")]

    operations = [
        migrations.AlterField(
            model_name="auditevent",
            name="action",
            field=models.CharField(
                choices=[
                    ("LOGIN_SUCCESS", "Login success"),
                    ("LOGIN_FAILED", "Login failed"),
                    ("SESSION_EXPIRED", "Session expired"),
                    ("USER_CREATED", "User created"),
                    ("USER_DISABLED", "User disabled"),
                    ("USER_ENABLED", "User enabled"),
                    ("ROLE_CHANGED", "Role changed"),
                    ("DONOR_UPDATED", "Donor updated"),
                    ("DONOR_PROFILE_CREATED", "Donor profile created"),
                    ("APPOINTMENT_BOOKED", "Appointment booked"),
                    ("APPOINTMENT_CANCELLED", "Appointment cancelled"),
                    ("DONATION_RECORDED", "Donation recorded"),
                    ("UNIT_CREATED", "Unit created"),
                    ("UNIT_RESERVED", "Unit reserved"),
                    ("UNIT_RELEASED", "Unit released"),
                    ("UNIT_ISSUED", "Unit issued"),
                    ("UNIT_EXPIRED", "Unit expired"),
                    ("UNIT_DISCARDED", "Unit discarded"),
                    ("UNIT_RETURNED", "Unit returned"),
                    ("REQUEST_SUBMITTED", "Request submitted"),
                    ("REQUEST_APPROVED", "Request approved"),
                    ("REQUEST_RESERVED", "Request reserved"),
                    ("REQUEST_REJECTED", "Request rejected"),
                    ("REQUEST_HELD", "Request held"),
                    ("REQUEST_FULFILLED", "Request fulfilled"),
                    ("THRESHOLD_CHANGED", "Threshold changed"),
                    ("LOW_STOCK_ALERTED", "Low stock alert created"),
                    ("ACCESS_DENIED", "Access denied"),
                    ("AUDIT_RETENTION_DRY_RUN", "Audit retention dry run"),
                    ("AUDIT_RETENTION_RUN", "Audit retention run"),
                ],
                db_index=True,
                max_length=64,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="auditevent", name="audit_action_catalogued"
        ),
        migrations.AddConstraint(
            model_name="auditevent",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    action__in=(
                        "LOGIN_SUCCESS", "LOGIN_FAILED", "SESSION_EXPIRED",
                        "USER_CREATED", "USER_DISABLED", "USER_ENABLED",
                        "ROLE_CHANGED", "DONOR_UPDATED", "DONOR_PROFILE_CREATED",
                        "APPOINTMENT_BOOKED", "APPOINTMENT_CANCELLED",
                        "DONATION_RECORDED", "UNIT_CREATED", "UNIT_RESERVED",
                        "UNIT_RELEASED", "UNIT_ISSUED", "UNIT_EXPIRED",
                        "UNIT_DISCARDED", "UNIT_RETURNED", "REQUEST_SUBMITTED",
                        "REQUEST_APPROVED", "REQUEST_RESERVED", "REQUEST_REJECTED",
                        "REQUEST_HELD", "REQUEST_FULFILLED", "THRESHOLD_CHANGED",
                        "LOW_STOCK_ALERTED", "ACCESS_DENIED",
                        "AUDIT_RETENTION_RUN", "AUDIT_RETENTION_DRY_RUN",
                    )
                ),
                name="audit_action_catalogued",
            ),
        ),
    ]
