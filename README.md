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

The current URL prefixes are `accounts/`, `donors/`, `inventory/`, `requests/`, `notifications/`, `administration/`, and `audit/`. Add a route inside the owning app instead of editing the project URL file for each feature.

Sprint work is assigned by the Scrum Master. Before coding, acknowledge the assigned issue, update local `main`, and create the issue branch described in `CONTRIBUTING.md`.
