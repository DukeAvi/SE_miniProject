# Blood Bank Management System

The project is an API-only Django application using Python 3.12+, Django 5.2, Django REST Framework, PostgreSQL, and Celery for scheduled inventory expiry. There is no frontend build step. Use the local SQLite demo for a quick start, or PostgreSQL and Redis for the full runtime.

## Install dependencies

From the repository root, create a virtual environment and install the pinned application and development tools:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

For runtime-only dependencies, install `requirements.txt` instead. The commands below assume the virtual environment is active.

## Quick local demo (SQLite)

The `bbms.settings_seed` settings use a disposable, Git-ignored SQLite database with DEBUG enabled. Migrate it, create synthetic Sprint 1 records, and start the API:

```bash
python manage.py migrate --noinput --settings=bbms.settings_seed
python manage.py seed_test_data --settings=bbms.settings_seed --as-of-date 2026-10-30
python manage.py runserver --settings=bbms.settings_seed
```

In another terminal, check `http://127.0.0.1:8000/healthz`. API routes are under `/api/v1/`; see the [API contract and Postman collection](docs/api/README.md). The seed accounts have unusable passwords. For a repeatable authenticated workflow using separate synthetic accounts, run:

```bash
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver python manage.py demo_sprint_one --settings=bbms.settings_seed
```

The seed command is safe to repeat with the same date. Its record counts and in-memory request/notification mocks are documented in the [seed-data guide](docs/qa/seed-test-data.md). The demo database does not require PostgreSQL or Redis.

## PostgreSQL runtime

Create a PostgreSQL database and user matching the `POSTGRES_*` values in `.env.example`. Copy the template to `.env` and set a local database password and Django secret key; `.env` is ignored by Git. Then migrate and start the API:

```bash
cp .env.example .env
python manage.py migrate --noinput
python manage.py runserver
```

The API runs without Redis, but the daily inventory expiry job needs Redis at `CELERY_BROKER_URL`. With Redis running, start a Celery worker and Beat in separate terminals using the same `.env`:

```bash
celery -A bbms worker --loglevel=INFO
celery -A bbms beat --loglevel=INFO
```

Beat schedules expiry at 00:05 in `BLOOD_BANK_TIME_ZONE`. See the [expiry operations guide](docs/operations/inventory-expiry.md) for monitoring, retries, and the test-only manual trigger. The demo notification provider writes sanitized console events; it does not send email or SMS.

## Checks

The test suite uses its own SQLite settings. Run these checks from the repository root:

```bash
ruff check .
python manage.py check --settings=bbms.settings_test
python manage.py makemigrations --check --dry-run --settings=bbms.settings_test
python scripts/validate_api_contract.py
pytest
git diff --check
```

Application behavior is implemented through its linked GitHub issues. See `CONTRIBUTING.md` before starting work.

## Application layout

The API is mounted at `/api/v1/`. Each application owns its URL prefix and keeps the same small set of modules:

- `urls.py` maps that application's endpoints.
- `serializers.py` validates API input and shapes responses.
- `views.py` handles HTTP concerns and calls the service layer.
- `services.py` contains business rules and database operations.
- `models.py` contains persisted domain state.

The OpenAPI contract and matching Postman collection are documented in [`docs/api/README.md`](docs/api/README.md).

Keep views short. Rules that need unit tests or are reused by more than one endpoint belong in `services.py` or a focused domain module. Add unit tests under `tests/unit/<app>/` and database or API-flow tests under `tests/integration/<app>/`.

Account routes are mounted directly under `/api/v1/` (for example, `/auth/`). The other current URL prefixes are `donors/`, `inventory/`, `requests/`, `notifications/`, `administration/`, and `audit/`. Add a route inside the owning app instead of editing the project URL file for each feature.

## Account registration

`POST /api/v1/auth/register` accepts `email`, `first_name`, `last_name`, `phone`, `password`, and `role`. Email addresses support up to 254 characters and are stored separately from the opaque, framework-internal username. The public role values are `DONOR` and `RECIPIENT`; staff and administrator accounts cannot be created through this endpoint. Email addresses and phone numbers are normalized before uniqueness checks, and password values are stored using Django's Argon2 hasher.

The v1.0 one-role-per-account behavior is approved under OI-5 (#88): a person acting as both Donor and Recipient uses two accounts. Multiple roles on one account remain future scope.

## Login and sessions

The API uses Django database-backed sessions. Fetch `GET /api/v1/auth/csrf` before a state-changing request and send the returned `csrfToken` in the `X-CSRFToken` header. Login is `POST /api/v1/auth/login` with `email` and `password`; successful responses include a role dashboard path. Logout is `POST /api/v1/auth/logout` and invalidates the current session. Unknown emails, incorrect passwords, disabled accounts, and accounts with no recognized role receive the same generic credential error.

Login failures are throttled by account and client IP. The defaults are five failures per 900-second window and are configurable with `LOGIN_THROTTLE_ATTEMPTS` and `LOGIN_THROTTLE_WINDOW_SECONDS`. The session cookie is HttpOnly and SameSite=Lax, and defaults to Secure when DEBUG is false. The CSRF cookie is SameSite=Lax, defaults to Secure when DEBUG is false, and is readable by the browser so clients can send its token in the header. Sessions renew their idle expiry on activity after 1200 seconds by default (`SESSION_IDLE_TIMEOUT_SECONDS`) and have an independent 28800-second absolute lifetime (`SESSION_ABSOLUTE_TIMEOUT_SECONDS`). The older `SESSION_COOKIE_AGE` variable remains a fallback for the idle timeout. Expired API sessions return `401 session_expired`; a browser UI is not present in this repository yet to implement its redirect behavior. Server-side session authentication is approved under OI-6 (#89), following SAD ADR-004.

## Credential and log protection

New and changed passwords use Django's Argon2 password hasher. The configured Django and application console handlers use `SensitiveDataFilter`, which redacts credential/token/session fields, contact and clinical fields, email addresses, phone numbers, and exception messages. Add the same filter to any additional log handler and avoid logging raw request bodies or user-provided values.

Sprint work is assigned by the Scrum Master. Before coding, acknowledge the assigned issue, update local `main`, and create the issue branch described in `CONTRIBUTING.md`.

## Notifications

The classroom demo uses `NOTIFICATION_PROVIDER=console` and does not send email or SMS. Automated tests use a deterministic mock adapter. Do not add provider credentials for the demo. Console output must omit message content, contact details, tokens, and clinical information. See `docs/decisions/OI-7-notification-provider.md` for the provider decision and failure-handling contract.
