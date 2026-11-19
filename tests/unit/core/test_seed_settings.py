import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module, overrides, expected",
    [
        ("bbms.settings_seed", {}, "True False False False True"),
        ("bbms.settings_seed", {"DJANGO_DEBUG": "false"}, "True False False False True"),
        ("bbms.settings_seed", {"SECURE_SSL_REDIRECT": "true", "SESSION_COOKIE_SECURE": "true", "CSRF_COOKIE_SECURE": "true"}, "True True True True True"),
        ("bbms.settings", {"DJANGO_DEBUG": "false", "POSTGRES_SSLMODE": "disable"}, "False True True True True"),
    ],
)
def test_demo_settings_defaults_and_explicit_overrides(module, overrides, expected):
    env = os.environ.copy()
    for key in ("DJANGO_DEBUG", "SECURE_SSL_REDIRECT", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE", "POSTGRES_SSLMODE", "POSTGRES_SSLROOTCERT"):
        env.pop(key, None)
    env.update(overrides)
    env.update(DJANGO_SETTINGS_MODULE=module, PYTHON_DOTENV_DISABLED="1")
    source = (
        "import os; original = os.environ.get('DJANGO_DEBUG'); "
        "from django.conf import settings; "
        "print(settings.DEBUG, settings.SECURE_SSL_REDIRECT, "
        "settings.SESSION_COOKIE_SECURE, settings.CSRF_COOKIE_SECURE, "
        "os.environ.get('DJANGO_DEBUG') == original)"
    )
    result = subprocess.run([sys.executable, "-c", source], env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == expected
