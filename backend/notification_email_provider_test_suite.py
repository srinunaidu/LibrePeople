"""Email provider selection + handler gating (LP-NOT-002).

What this suite proves
-----------------------
* ``get_provider`` returns the log provider by default and the SMTP
  provider when ``EMAIL_PROVIDER=smtp`` (no network call to select it).
* The SMTP provider is stdlib-only: no vendor SDK is imported.
* The delivery handler calls the provider only when the recipient still
  has the email channel on, and sets ``email_sent`` only when the
  provider returns. A provider failure propagates (so the queue marks
  the row failed/retried) and leaves ``email_sent`` False.
* ``.env.example`` documents the EMAIL_PROVIDER/SMTP_* placeholders.

Run:  python notification_email_provider_test_suite.py
"""
import datetime
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="notification_email_provider_"), "suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"
# Provider selection must default to log even if the shell exports SMTP.
for _key in ("EMAIL_PROVIDER", "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME",
             "SMTP_PASSWORD", "SMTP_USE_TLS", "SMTP_FROM"):
    os.environ.pop(_key, None)

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.ess_hr import EmployeeSelfService, Notification  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import email_provider as ep  # noqa: E402
import app.jobs.handlers as handlers  # noqa: E402

Base.metadata.create_all(bind=engine)

RESULTS = {"pass": 0, "fail": 0}
FAILURES: list[tuple[str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


# --- fixtures ---------------------------------------------------------------
db = SessionLocal()
dept = Department(name="Email", code="EML")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Courier", code="EMLJOB", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)


def _employee(code: str) -> Employee:
    emp = Employee(
        employee_id=code, first_name="Email", last_name=code,
        email=f"{code.lower()}@example.com", hire_date=datetime.date(2024, 1, 1),
        job_id=job.id, department_id=dept.id, status="Active",
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


emp_on = _employee("EML-ON")
emp_off = _employee("EML-OFF")


def _user(username: str, employee_id: int | None) -> int:
    u = User(username=username, email=f"{username}@example.com",
             hashed_password=get_password_hash("Pass12345abc"), role="Associate",
             is_active=True, employee_id=employee_id, mfa_enabled=False)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u.id


on_id = _user("eml_on", emp_on.id)
off_id = _user("eml_off", emp_off.id)
# The opt-out recipient: every channel flag off.
db.add(EmployeeSelfService(employee_id=emp_off.id, notification_email=False,
                           notification_sms=False, notification_push=False))
db.commit()


def _notif(recipient_id: int, tag: str) -> Notification:
    row = Notification(recipient_id=recipient_id, title=f"Email {tag}",
                       message="hello", notification_type="info", category="system",
                       entity_type="probe", entity_id=abs(hash(tag)) % 10**9,
                       delivery_status="queued", delivery_attempts=0)
    db.add(row)
    db.commit()
    db.refresh(row)
    row.email_sent = False
    return row


# ===========================================================================
print("\n[PROV-01] Provider selection defaults to log, smtp on request")
# ===========================================================================
check("default provider is the log provider",
      type(ep.get_provider()).__name__ == "LogProvider",
      f"got {type(ep.get_provider()).__name__}")
os.environ["EMAIL_PROVIDER"] = "smtp"
os.environ["SMTP_HOST"] = "smtp.example.invalid"
try:
    selected = ep.get_provider()
    check("EMAIL_PROVIDER=smtp selects the SMTP provider",
          type(selected).__name__ == "SmtpProvider",
          f"got {type(selected).__name__}")
    check("the SMTP host comes from the environment",
          getattr(selected, "host", "") == "smtp.example.invalid",
          f"host={getattr(selected, 'host', None)!r}")
finally:
    os.environ.pop("EMAIL_PROVIDER", None)
    os.environ.pop("SMTP_HOST", None)
check("selection makes no network call (still default after cleanup)",
      type(ep.get_provider()).__name__ == "LogProvider")
try:
    ep.SmtpProvider(host="  ")
    check("SMTP provider without a host is refused", False, "no error raised")
except ValueError:
    check("SMTP provider without a host is refused", True)


# ===========================================================================
print("\n[PROV-02] No vendor SDK; stdlib SMTP only")
# ===========================================================================
import pathlib

source_path = pathlib.Path(__file__).resolve().parent / "app" / "services" / "email_provider.py"
source = source_path.read_text()
import re

banned = [name for name in ("boto", "sendgrid", "mailgun", "postmark", "mailchimp", "resend")
          if re.search(rf"(?i)(?:^|[^a-z]){re.escape(name)}(?:[^a-z]|$)", source)]
# AWS SES counts only as an actual import/reference, not a substring of "raises".
if re.search(r"(?i)\bimport\b[^\n]*\bses\b", source) or re.search(r"(?i)\bfrom\b[^\n]*\bses\b", source):
    banned.append("ses")
check("no vendor SDK is referenced",
      not banned, f"found {banned}")
check("SMTP goes through the standard library",
      "import smtplib" in source, "smtplib import missing")
check("the log provider succeeds without SMTP",
      ep.LogProvider().send("a@example.com", "s", "b") is None)


# ===========================================================================
print("\n[PROV-03] Handler calls the provider only when email is on")
# ===========================================================================
calls: list[tuple[str, str, str]] = []


class FakeProvider:
    def send(self, to: str, subject: str, body: str) -> None:
        calls.append((to, subject, body))


real_get_provider = ep.get_provider


def _fake() -> FakeProvider:
    return FakeProvider()


import app.services.email_provider as _ep_module

_ep_module.get_provider = _fake  # type: ignore[method-assign]
try:
    row = _notif(on_id, "pref-on")
    out = handlers._deliver_channels(db, row)
    check("provider called once when email is on",
          len(calls) == 1 and calls[0][0] == "eml_on@example.com"
          and calls[0][1] == row.title and calls[0][2] == row.message,
          f"calls={calls!r}")
    check("email_sent set after the provider returns",
          row.email_sent is True and out["email"] is True)
    db.delete(row)
    db.commit()

    calls.clear()
    row2 = _notif(off_id, "pref-off")
    out2 = handlers._deliver_channels(db, row2)
    check("provider never called when every channel is off",
          calls == [], f"calls={calls!r}")
    check("email stays unsent when the preference is off",
          row2.email_sent is False and out2["email"] is False)
    db.delete(row2)
    db.commit()
finally:
    _ep_module.get_provider = real_get_provider  # type: ignore[method-assign]


# ===========================================================================
print("\n[PROV-04] email_sent is set only on real success")
# ===========================================================================
class BoomProvider:
    def send(self, to: str, subject: str, body: str) -> None:
        raise RuntimeError("smtp unreachable (simulated)")


_ep_module.get_provider = lambda: BoomProvider()  # type: ignore[assignment]
try:
    row3 = _notif(on_id, "boom")
    try:
        handlers._deliver_channels(db, row3)
        check("a provider failure propagates to the retry path", False, "no error raised")
    except RuntimeError:
        check("a provider failure propagates to the retry path", True)
    db.refresh(row3)
    check("email_sent stays False after a failed send",
          row3.email_sent is False, f"email_sent={row3.email_sent!r}")
    db.delete(row3)
    db.commit()
finally:
    _ep_module.get_provider = real_get_provider  # type: ignore[method-assign]


# ===========================================================================
print("\n[PROV-05] .env.example documents placeholders, not credentials")
# ===========================================================================
root_example = pathlib.Path("..") / ".env.example"
if not root_example.exists():
    root_example = pathlib.Path("/Users/srinivas/LLM/Workforce/librepeople-prod/.env.example")
example = root_example.read_text()
for key in ("EMAIL_PROVIDER=", "SMTP_HOST=", "SMTP_PORT=", "SMTP_USERNAME=",
            "SMTP_PASSWORD=", "SMTP_USE_TLS=", "SMTP_FROM="):
    check(f".env.example documents {key.rstrip('=')}",
          key in example, f"missing {key}")
check(".env.example keeps placeholders, not real credentials",
      "change-me" in example or "example.com" in example)


print("\n" + "=" * 62)
print(f"==== EMAIL PROVIDER SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 62)
raise SystemExit(1 if RESULTS["fail"] else 0)
