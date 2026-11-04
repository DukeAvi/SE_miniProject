import os

# The in-memory suite does not open the PostgreSQL connection. Keep the test
# configuration explicit so importing production settings needs no DB CA file.
os.environ["POSTGRES_SSLMODE"] = "disable"

from .settings import *  # noqa: F403,E402


DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

SECURE_SSL_REDIRECT = False  # noqa: F405
SECURE_HSTS_SECONDS = 0  # noqa: F405
