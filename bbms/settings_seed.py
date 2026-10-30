"""Local-only SQLite settings for repeatable synthetic seed data."""

from .settings import *  # noqa: F403


DEBUG = True
DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / ".bbms-seed.sqlite3",  # noqa: F405
    }
}
