import logging

from django.conf import settings

from apps.core.logging import REDACTED, SensitiveDataFilter


class CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def logger_with_filter():
    logger = logging.getLogger("bbms.tests.sensitive-data")
    logger.handlers.clear()
    logger.filters.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)
    handler = CaptureHandler()
    handler.addFilter(SensitiveDataFilter())
    logger.addHandler(handler)
    return logger, handler


def test_sensitive_log_arguments_and_extra_fields_are_redacted():
    logger, handler = logger_with_filter()
    logger.warning(
        "login password=%s token=%s session_id=%s email=%s phone=%s blood_group=%s",
        "pw-secret-781",
        "token-secret-298",
        "session-secret-552",
        "patient@example.test",
        "+1 202-555-0142",
        "AB-",
        extra={
            "access_token": "extra-token-123",
            "date_of_birth": "1980-01-02",
            "diagnosis": "sensitive diagnosis",
            "safe_context": "arbitrary user text",
        },
    )

    record = handler.records[0]
    message = record.getMessage()
    assert record.levelname == "WARNING"
    assert record.name == "bbms.tests.sensitive-data"
    for secret in (
        "pw-secret-781",
        "token-secret-298",
        "session-secret-552",
        "patient@example.test",
        "+1 202-555-0142",
        "AB-",
    ):
        assert secret not in message
    assert record.access_token == REDACTED
    assert record.date_of_birth == REDACTED
    assert record.diagnosis == REDACTED
    assert record.safe_context == REDACTED


def test_sensitive_json_and_exception_messages_are_redacted():
    logger, handler = logger_with_filter()
    logger.error(
        'request payload={"email":"private@example.test","password":"literal-secret"}'
    )
    logger.error("Authorization: Bearer authorization-secret-991")
    try:
        raise ValueError("raw-session-secret-992 phone=+442079460123")
    except ValueError:
        logger.exception("authentication failed")

    assert "private@example.test" not in handler.records[0].getMessage()
    assert "literal-secret" not in handler.records[0].getMessage()
    assert "authorization-secret-991" not in handler.records[1].getMessage()
    assert "raw-session-secret-992" not in handler.records[2].exc_text
    assert "+442079460123" not in handler.records[2].exc_text


def test_application_and_django_handlers_use_the_redaction_filter():
    assert settings.LOGGING["handlers"]["console"]["filters"] == ["sensitive_data"]
    for logger_name in (
        "django",
        "django.request",
        "django.security",
        "django.server",
        "django.db.backends",
        "apps",
    ):
        assert settings.LOGGING["loggers"][logger_name]["handlers"] == ["console"]
    for logger_name in (
        "",
        "django",
        "django.request",
        "django.security",
        "django.server",
        "django.db.backends",
        "apps",
    ):
        logger = logging.getLogger(logger_name)
        assert logger.handlers
        assert any(
            any(isinstance(log_filter, SensitiveDataFilter) for log_filter in handler.filters)
            for handler in logger.handlers
        )
    assert settings.PASSWORD_HASHERS[0] == "django.contrib.auth.hashers.Argon2PasswordHasher"
