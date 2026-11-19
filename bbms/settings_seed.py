"""Local-only SQLite settings for repeatable synthetic seed data."""

import os

# Base settings derive database and cookie defaults from DEBUG at import time.
# Use local defaults while loading them, then restore the caller's environment.
_original_debug = os.environ.get("DJANGO_DEBUG")
os.environ["DJANGO_DEBUG"] = "true"
try:
    from .settings import *  # noqa: F403
finally:
    if _original_debug is None:
        os.environ.pop("DJANGO_DEBUG", None)
    else:
        os.environ["DJANGO_DEBUG"] = _original_debug


DEBUG = True
DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / ".bbms-seed.sqlite3",  # noqa: F405
    }
}
