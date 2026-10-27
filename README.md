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
