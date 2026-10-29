# API v1 contract

`openapi.json` is the OpenAPI 3.0.3 contract for the `/api/v1` service (DOC-001; SAD Next Step 3). It includes every endpoint listed in SAD Section 4.3 plus the implemented CSRF bootstrap endpoint. The `x-implementation-status` extension distinguishes routes already mounted in Django from planned routes in the backlog; the contract does not claim that planned routes are implemented. Security and role declarations follow approved OI-4 (#87) and OI-6 (#89).

`BBMS-API-v1.postman_collection.json` contains synthetic requests generated from the same operation list. It has no account password, session value, CSRF token, or provider credential. Postman keeps the session cookie in its local cookie jar. Set demo account values only in a local Postman environment.

To use the collection locally:

1. Import the collection into Postman.
2. Set `baseUrl` to `http://127.0.0.1:8000`.
3. Set `demoEmail` and `demoPassword` locally to synthetic demo-account credentials.
4. Run the `Implemented routes smoke` folder against a clean local database. It obtains a CSRF token, registers and logs in the demo account, refreshes the CSRF token after login rotates it, reads and updates the profile, then logs out. Postman retains the session cookie in its local cookie jar.
5. The `Planned endpoints` folder is contract reference material; its operations require their implementation issues to land before they can be executed. Replace sample query and path variables with valid demo values when appropriate.

Validate JSON structure, role/security declarations, error envelopes, idempotency, Postman parity, and all routes currently mounted in Django with:

```text
python scripts/validate_api_contract.py
```

The executable Postman smoke can be run against a clean local database and server with Newman. Set the demo values locally; do not save real credentials in the collection:

```text
npm exec --yes --package=newman -- newman run docs/api/BBMS-API-v1.postman_collection.json --folder 'Implemented routes smoke' --env-var baseUrl=http://127.0.0.1:8000 --env-var demoEmail=demo@example.invalid --env-var demoPassword='Replace-With-Local-Only-Password'
```

The current application implements the health, auth/CSRF, profile, donation slot listing, appointment booking/history/cancellation, and donation-recording/history routes. Donation operations use synthetic demo data, `BLOOD_BANK_TIME_ZONE` (default `Asia/Kolkata`), and `DONATION_SLOT_CAPACITY` (default 10). Booking and cancellation require a seeded donor profile and slot; staff donation recording requires a seeded staff account and donor profile. The complete repeatable setup is tracked in QA-001 (#95).
