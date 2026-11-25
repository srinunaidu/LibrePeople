"""Structured logging, request correlation and redaction.

Why
---
Before this, the app used bare ``print`` and ad-hoc logging. That makes three
operational questions unanswerable: which log lines belong to one user
request, what actually failed, and whether a line contains a secret.

What this provides
------------------
* **Correlation id** — every request gets an id (honouring an inbound
  ``X-Request-ID`` so a trace survives across services), it is attached to the
  log context and echoed back to the caller.
* **Structured logs** — one JSON object per line with stable field names, so a
  log aggregator can filter instead of regex-parsing prose.
* **Redaction** — a recursive scrubber that removes anything whose key looks
  like a credential, so adding a new endpoint cannot accidentally start
  logging passwords.

Never logged, by design: passwords, bearer tokens, wallet passwords, database
DSNs, bank account numbers, tax identifiers. ``redact`` handles the last group
by key name; callers must still avoid passing raw secrets in ``detail=``.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)

#: Keys whose values are replaced wholesale, whatever their nesting.
SENSITIVE_KEYS = frozenset({
    "password", "passwd", "secret", "token", "access_token", "refresh_token",
    "authorization", "api_key", "apikey", "client_secret", "private_key",
    "wallet_password", "hashed_password", "bank_account", "account_number",
    "tax_id", "ssn", "national_insurance", "card_number", "cvv", "iban",
    "dsn", "connection_string", "dsn_configured_value",
})

REDACTED = "***redacted***"

_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def redact(value: Any, _depth: int = 0) -> Any:
    """Recursively replace sensitive-looking values."""
    if _depth > 8:
        return "<max-depth>"
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if isinstance(k, str) and k.lower() in SENSITIVE_KEYS:
                out[k] = REDACTED
            else:
                out[k] = redact(v, _depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [redact(v, _depth + 1) for v in value]
    return value


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def set_request_id(value: str | None) -> str:
    rid = value or new_request_id()
    _request_id.set(rid)
    return rid


def get_request_id() -> str | None:
    return _request_id.get()


#: The hashed client address of the request being served. It is a ContextVar
#: rather than a parameter so the audit helper can record it without every
#: endpoint growing a `request` argument. Only the digest is stored: the raw
#: address is personal data and the audit trail does not need it to answer
#: "was this action taken from the same place as the others?".
_client_ip_hash: ContextVar[str | None] = ContextVar("client_ip_hash", default=None)


def set_client_ip(value: str | None) -> str | None:
    """Remember the client address for this request, as a SHA-256 digest."""
    if not value:
        _client_ip_hash.set(None)
        return None
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    _client_ip_hash.set(digest)
    return digest


def get_client_ip_hash() -> str | None:
    return _client_ip_hash.get()


class JsonFormatter(logging.Formatter):
    """One JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        rid = get_request_id()
        if rid:
            payload["request_id"] = rid

        # Anything passed via `extra={"ctx": {...}}` is merged in.
        ctx = getattr(record, "ctx", None)
        if isinstance(ctx, dict):
            payload.update(redact(ctx))

        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["exc"] = redact(self.formatException(record.exc_info).splitlines()[-1])

        return json.dumps(payload, default=str)


class StructuredLogger:
    """Thin wrapper so call sites read as log.info("msg", action=..., id=...)."""

    def __init__(self, name: str):
        self._log = logging.getLogger(name)

    def _emit(self, level: int, msg: str, **ctx: Any) -> None:
        if not self._log.isEnabledFor(level):
            return
        self._log.log(level, msg, extra={"ctx": ctx})

    def debug(self, msg: str, **ctx: Any) -> None:
        self._emit(logging.DEBUG, msg, **ctx)

    def info(self, msg: str, **ctx: Any) -> None:
        self._emit(logging.INFO, msg, **ctx)

    def warning(self, msg: str, **ctx: Any) -> None:
        self._emit(logging.WARNING, msg, **ctx)

    def error(self, msg: str, **ctx: Any) -> None:
        self._emit(logging.ERROR, msg, **ctx)

    def exception(self, msg: str, **ctx: Any) -> None:
        self._log.error(msg, extra={"ctx": ctx}, exc_info=True)


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)


def configure_logging(level: str | None = None) -> None:
    """Install the JSON formatter on the root logger. Idempotent."""
    lvl = _LEVELS.get((level or "INFO").upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(lvl)
    # Replace our own handlers only; leave third-party handlers alone.
    for h in list(root.handlers):
        if getattr(h, "_karmathy", False):
            root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._karmathy = True  # type: ignore[attr-defined]
    root.addHandler(handler)