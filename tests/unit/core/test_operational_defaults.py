from pathlib import Path

import pytest
from django.conf import settings

from bbms.settings import env_positive_int, env_time_zone

APPROVED_DEFAULTS = {
    "BLOOD_BANK_TIME_ZONE": "Asia/Kolkata",
    "DONATION_SLOT_CAPACITY": "10",
    "DEFAULT_STOCK_THRESHOLD": "5",
    "BACKUP_RETENTION_DAYS": "7",
}


def read_env_example():
    lines = (Path(settings.BASE_DIR) / ".env.example").read_text().splitlines()
    return dict(
        line.split("=", 1)
        for line in lines
        if "=" in line and not line.startswith("#")
    )


def test_env_example_uses_approved_defaults():
    values = read_env_example()
    for name, expected in APPROVED_DEFAULTS.items():
        assert values[name] == expected


@pytest.mark.parametrize("value", ["1", "5", "365"])
def test_positive_int_accepts_positive_values(monkeypatch, value):
    monkeypatch.setenv("DEFAULT_STOCK_THRESHOLD", value)
    assert env_positive_int("DEFAULT_STOCK_THRESHOLD", 5) == int(value)


@pytest.mark.parametrize("value", ["0", "-1", "abc", "", "2.5"])
def test_positive_int_rejects_unsafe_values(monkeypatch, value):
    monkeypatch.setenv("BACKUP_RETENTION_DAYS", value)
    with pytest.raises(ValueError):
        env_positive_int("BACKUP_RETENTION_DAYS", 7)


def test_positive_int_uses_default_when_unset(monkeypatch):
    monkeypatch.delenv("BACKUP_RETENTION_DAYS", raising=False)
    assert env_positive_int("BACKUP_RETENTION_DAYS", 7) == 7


def test_time_zone_accepts_valid_name(monkeypatch):
    monkeypatch.setenv("BLOOD_BANK_TIME_ZONE", "Asia/Kolkata")
    assert env_time_zone("BLOOD_BANK_TIME_ZONE", "UTC") == "Asia/Kolkata"


@pytest.mark.parametrize("value", ["Mars/Phobos", "", "../etc/passwd"])
def test_time_zone_rejects_invalid_names(monkeypatch, value):
    monkeypatch.setenv("BLOOD_BANK_TIME_ZONE", value)
    with pytest.raises(ValueError):
        env_time_zone("BLOOD_BANK_TIME_ZONE", "Asia/Kolkata")
