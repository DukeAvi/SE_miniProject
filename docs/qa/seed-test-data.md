# Sprint 1 synthetic seed data (QA-001)

Use the local SQLite settings to initialize a disposable database, then run the one seed command. The database file is ignored by Git. Use only synthetic `example.test` accounts; their passwords are unusable. The command refuses non-DEBUG settings or a non-SQLite database.

```sh
.venv/bin/python manage.py migrate --noinput --settings=bbms.settings_seed
.venv/bin/python manage.py seed_test_data --settings=bbms.settings_seed --as-of-date 2026-10-30
```

Run the seed command again with the same date to verify idempotence. The JSON summary must stay at 14 users across all four roles, 11 donor profiles, 8 completed donations, 32 units covering every blood group and component, 2 slots, and 2 appointments. One unit is expired on the test date and one expires the next day. Three additional donor profiles cover the exact age, weight, and donation-interval eligibility boundaries.

The summary also lists five synthetic request states and five notification deliveries. These are **in-memory mocks** because persistent request and notification-outbox models are outside Sprint 1. `MockNotificationOutbox` supports deterministic delivered and failed events without contacting a provider. No request or notification outbox rows are created by this command.

The command does not create a login password. Use the existing `demo_sprint_one` command for an authenticated API walkthrough; tests can use `force_authenticate` for seed records. Delete the local SQLite file when the demo is finished.

Traceability: QA-001; SAD 3.8.2 and next step 6; Software Test Plan sections 6 and 11; `tests/integration/test_seed_test_data.py`.
