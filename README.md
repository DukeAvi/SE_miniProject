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

Keep views short. Rules that need unit tests or are reused by more than one endpoint belong in `services.py` or a focused domain module. Add unit tests under `tests/unit/<app>/` and database or API-flow tests under `tests/integration/<app>/`.

Account routes are mounted directly under `/api/v1/` (for example, `/auth/`). The other current URL prefixes are `donors/`, `inventory/`, `requests/`, `notifications/`, `administration/`, and `audit/`. Add a route inside the owning app instead of editing the project URL file for each feature.

## Account registration

`POST /api/v1/auth/register` accepts `email`, `first_name`, `last_name`, `phone`, `password`, and `role`. Email addresses support up to 254 characters and are stored separately from the opaque, framework-internal username. The public role values are `DONOR` and `RECIPIENT`; staff and administrator accounts cannot be created through this endpoint. Email addresses and phone numbers are normalized before uniqueness checks, and password values are stored using Django's Argon2 hasher.

The v1.0 one-role-per-account behavior follows the SAD proposal and remains provisional pending product-owner confirmation under issue #88.

Sprint work is assigned by the Scrum Master. Before coding, acknowledge the assigned issue, update local `main`, and create the issue branch described in `CONTRIBUTING.md`.
