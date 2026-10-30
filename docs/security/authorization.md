# Server authorization (BBMS-SR-002 / DS-SR-002 / TC-Sec-02)

All mounted API views declare an explicit public or authenticated permission policy. Role-bound views use `RolePermission` and the approved matrix in `docs/decisions/OI-4-admin-staff-separation.md`. The mounted-view inventory in `tests/unit/core/test_active_authorization.py` fails if a later endpoint omits a policy or uses an unknown role code.

Sensitive donor and inventory services recheck the actor's role and active status before loading or changing records. Profile updates reject inactive accounts. Appointment cancellation and profile routes restrict access to the signed-in owner; foreign and missing appointment IDs return the same 404 response shape. The role matrix is tested for every role and operation in `tests/unit/core/test_permissions.py`, with direct-service, inactive-account, and ownership cases in the adjacent unit and donor integration tests.

As new request, notification, administration, and audit endpoints are implemented, their owning issues must add operation-specific API and direct-service authorization cases. The mounted-view test continues to enforce an explicit policy for each route.
