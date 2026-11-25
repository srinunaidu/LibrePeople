"""Email delivery providers (LP-NOT-002).

Why this module exists
----------------------
LP-NOT-001 emitted in-app notifications and LP-NOT-003 delivered them
through the background queue, but the email channel was stubbed: the
handler set ``email_sent`` without calling any provider. This module is
the real email path, kept deliberately small:

* :class:`EmailProvider` is the interface the handler calls. It has one
  method, :meth:`send`, which returns on success and raises on failure
  so the queue's existing retry/backoff/dead-letter machinery (unchanged
  by this slice) applies without any new retry logic.
* :class:`LogProvider` is the default. It logs the send and succeeds.
  Tests and deployments without SMTP get a no-op that still records
  intent honestly (``email_sent`` means "handed to the provider").
* :class:`SmtpProvider` sends through any SMTP relay with the standard
  library only (:mod:`smtplib` + :mod:`email.message`). No vendor SDK
  is imported anywhere in this module, so there is nothing new to add
  to ``requirements.txt`` and nothing vendor-specific to mock.
* :func:`get_provider` selects the provider from the environment:
  ``EMAIL_PROVIDER=log`` (default) or ``smtp`` with ``SMTP_*`` settings.

The handler calls the provider only when the recipient still has the
email channel on, and sets ``email_sent`` only when the provider
returns. A provider failure propagates, so the row is marked
``failed``/``dead`` and the job is retried exactly as before.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Protocol

log = logging.getLogger("karmathy.email")


class EmailProvider(Protocol):
    """The interface every email provider implements."""

    def send(self, to: str, subject: str, body: str) -> None:
        """Send one email, or raise on failure.

        Returns ``None`` on success. Any exception means the send did
        not happen and the caller must treat the email as unsent.
        """
        ...  # pragma: no cover - interface only


class LogProvider:
    """The default provider: log the send, deliver nothing externally."""

    def send(self, to: str, subject: str, body: str) -> None:
        log.info("email to=%s subject=%s (log provider; no SMTP)", to, subject)


class SmtpProvider:
    """Send through any SMTP relay with the standard library only."""

    def __init__(
        self,
        host: str,
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        from_addr: str | None = None,
    ) -> None:
        if not (host or "").strip():
            raise ValueError("SMTP_HOST is required for the smtp email provider")
        self.host = host.strip()
        self.port = int(port)
        self.username = username or None
        self.password = password or None
        self.use_tls = bool(use_tls)
        self.from_addr = (from_addr or username or "").strip() or "no-reply@localhost"

    def send(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self.from_addr
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body or "")
        with smtplib.SMTP(self.host, self.port, timeout=30) as client:
            client.ehlo()
            if self.use_tls:
                client.starttls()
                client.ehlo()
            if self.username:
                client.login(self.username, self.password or "")
            client.send_message(message)


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is not None:
        return value
    try:
        from app.core.config import settings  # lazy: keeps import order simple

        return str(getattr(settings, name, default) or default)
    except Exception:  # noqa: BLE001
        return default


def get_provider() -> EmailProvider:
    """The email provider this deployment is configured to use.

    ``EMAIL_PROVIDER`` selects it: ``smtp`` for :class:`SmtpProvider`,
    anything else (including unset) for :class:`LogProvider`. SMTP
    connection details come from ``SMTP_HOST``/``SMTP_PORT``/
    ``SMTP_USERNAME``/``SMTP_PASSWORD``/``SMTP_USE_TLS``/``SMTP_FROM``.
    """
    name = _env("EMAIL_PROVIDER", "log").strip().lower() or "log"
    if name == "smtp":
        use_tls_raw = _env("SMTP_USE_TLS", "true").strip().lower()
        return SmtpProvider(
            host=_env("SMTP_HOST", ""),
            port=int(_env("SMTP_PORT", "587") or "587"),
            username=_env("SMTP_USERNAME", "") or None,
            password=_env("SMTP_PASSWORD", "") or None,
            use_tls=use_tls_raw not in ("0", "false", "no", "off"),
            from_addr=_env("SMTP_FROM", "") or None,
        )
    return LogProvider()


__all__ = ["EmailProvider", "LogProvider", "SmtpProvider", "get_provider"]
