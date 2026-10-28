"""Central redaction for application and Django log records."""

import re
import traceback
from collections.abc import Mapping
from logging import Filter


REDACTED = "[REDACTED]"
SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "token",
    "authorization",
    "session",
    "cookie",
    "email",
    "phone",
    "contact",
    "address",
    "name",
    "dateofbirth",
    "dob",
    "weight",
    "bloodgroup",
    "bloodtype",
    "clinical",
    "clinic",
    "medical",
    "medicalrecord",
    "health",
    "eligibility",
    "patient",
    "diagnosis",
)
SENSITIVE_VALUE_PATTERN = re.compile(
    r"""(?i)(?P<prefix>["']?(?:password|passwd|access[_-]?token|refresh[_-]?token|token|"""
    r"""authorization|session(?:id|[_-]?id)?|cookie|email|phone|contact|address|name|"""
    r"""date[_-]?of[_-]?birth|dob|weight|blood[_-]?(?:group|type)|clinical|clinic|"""
    r"""medical(?:[_-]?record)?|health|eligibility|patient|diagnosis)"""
    r"""["']?\s*[:=]\s*)(?P<value>(?:Bearer|Basic)\s+[^,;}\s]+|"[^"]*"|'[^']*'|[^,;}\s]+)"""
)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\w)\+?\d(?:[\s().-]*\d){7,14}(?!\w)")
JWT_PATTERN = re.compile(
    r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
)
STANDARD_RECORD_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
}


def _sensitive_key(key) -> bool:
    normalized = str(key).lower().replace("_", "").replace("-", "")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _redact_text(value: str) -> str:
    def redact_sensitive_field(match):
        field_value = match.group("value").strip("\"'")
        if field_value.startswith("%"):
            return match.group(0)
        return match.group("prefix") + REDACTED

    value = SENSITIVE_VALUE_PATTERN.sub(redact_sensitive_field, value)
    value = EMAIL_PATTERN.sub(REDACTED, value)
    value = PHONE_PATTERN.sub(REDACTED, value)
    return JWT_PATTERN.sub(REDACTED, value)


def _redact_value(value, *, redact_all_strings: bool = False):
    if isinstance(value, Mapping):
        return {
            key: REDACTED if _sensitive_key(key) else _redact_value(item, redact_all_strings=True)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(_redact_value(item, redact_all_strings=True) for item in value)
    if isinstance(value, list):
        return [_redact_value(item, redact_all_strings=True) for item in value]
    if isinstance(value, str):
        return REDACTED if redact_all_strings else _redact_text(value)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return REDACTED


class SensitiveDataFilter(Filter):
    """Redact credentials, tokens, session values, and sensitive user fields."""

    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = _redact_text(record.msg)
        else:
            record.msg = _redact_value(record.msg)
        if record.args:
            record.args = _redact_value(record.args, redact_all_strings=True)

        for key, value in tuple(record.__dict__.items()):
            if key in STANDARD_RECORD_FIELDS:
                continue
            if _sensitive_key(key):
                record.__dict__[key] = REDACTED
            elif isinstance(value, (str, Mapping, tuple, list)):
                record.__dict__[key] = _redact_value(value, redact_all_strings=True)
            elif not (value is None or isinstance(value, (int, float, bool))):
                record.__dict__[key] = REDACTED

        if record.exc_info:
            exception_type, _, exception_traceback = record.exc_info
            frames = traceback.extract_tb(exception_traceback)
            record.exc_text = "".join(
                f'  File "{_redact_text(frame.filename)}", line {frame.lineno}, in {frame.name}\n'
                for frame in frames
            )
            record.exc_text += f"{exception_type.__name__}: {REDACTED}\n"
            record.exc_info = None
        elif record.exc_text:
            record.exc_text = _redact_text(record.exc_text)
        if record.stack_info:
            record.stack_info = _redact_text(record.stack_info)
        return True
