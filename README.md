# Blood Bank Management System

The project uses Python 3.12+, Django 5.2, Django REST Framework, and PostgreSQL.

## Local setup

Create and activate a virtual environment, then install the pinned dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy the environment template and update the local PostgreSQL credentials:

```bash
cp .env.example .env
```

Create the configured PostgreSQL database, then initialize it:

```bash
python manage.py migrate
```

Start the development server with:

```bash
python manage.py runserver
```

The health endpoint is available at `http://127.0.0.1:8000/healthz`.

## Checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
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
