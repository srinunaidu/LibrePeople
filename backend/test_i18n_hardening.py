"""i18n consistency hardening — CSV BOM invariant + IN-only INR gate (pytest).

Covers two backend invariants from the i18n consistency slice:

1. **CSV framing invariant**: every CSV built by
   ``app.services.report_exports.rows_to_csv`` begins with U+FEFF, and the
   ``/reports`` CSV download serves those BOM-first bytes as
   ``text/csv; charset=utf-8``. Decode with ``utf-8-sig`` to recover the
   plain header-first text.
2. **Pay-run currency gate**: ``POST /payroll/runs`` with jurisdiction
   ``IN`` and a non-INR currency is refused with 422
   (``non_inr_currency``); ``IN``+``INR`` and non-IN jurisdictions keep
   working.

Run:  pytest test_i18n_hardening.py   (from ``backend/``)
"""
from __future__ import annotations

import os
import tempfile
from datetime import date

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="i18n_hardening_test_"), "i18n_hardening_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the module builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.payroll import PayrollPeriod  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import report_exports  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
db.add(User(username="i18n_hr", email="i18n_hr@example.com",
            hashed_password=get_password_hash("I18nPass12345"),
            role="HR", is_active=True, mfa_enabled=True))
# HR creates pay runs (ADMIN_ROLES) and reads reports (REPORTS_ROLES); the
# account-state gate refuses MFA-enforced roles before endpoint logic runs,
# so the fixture account is enrolled the way a real HR account is.
period = PayrollPeriod(name="I18N 2026-05", start_date=date(2026, 5, 1),
                       end_date=date(2026, 5, 31), pay_date=date(2026, 5, 15))
db.add(period)
db.commit()
db.refresh(period)
PERIOD_ID = period.id
db.close()

client = TestClient(app, raise_server_exceptions=False)


def _auth() -> dict:
    r = client.post("/api/v1/auth/login",
                    json={"username": "i18n_hr", "password": "I18nPass12345"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


HEADERS = _auth()

ROWS = [{"employee_id": "IN-1", "name": "अनिल कुमार", "gross": "876543.21"}]
COLUMNS = ["employee_id", "name", "gross"]


def test_rows_to_csv_starts_with_bom():
    text = report_exports.rows_to_csv(ROWS, COLUMNS)
    assert text.startswith("\ufeff"), f"missing BOM: {text[:20]!r}"


def test_rows_to_csv_sig_decode_recovers_header_first_text():
    text = report_exports.rows_to_csv(ROWS, COLUMNS)
    plain = text.encode("utf-8").decode("utf-8-sig")
    assert plain.splitlines()[0] == ",".join(COLUMNS), plain.splitlines()[0]
    assert "अनिल कुमार" in plain  # non-ASCII survives the round trip


def test_joiners_csv_download_serves_bom_bytes():
    r = client.get("/api/v1/reports/joiners", headers=HEADERS,
                   params={"from": "2026-01-01", "to": "2026-12-31", "format": "csv"})
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers.get("content-type", "")
    assert r.content.startswith(b"\xef\xbb\xbf"), r.content[:12]
    assert r.content.decode("utf-8-sig").splitlines()[0].startswith("employee_id")


def test_create_in_run_with_non_inr_currency_is_rejected_422():
    r = client.post("/api/v1/payroll/runs", headers=HEADERS,
                    json={"period_id": PERIOD_ID, "jurisdiction": "IN", "currency": "USD"})
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "non_inr_currency", r.text


def test_create_in_run_with_inr_is_accepted():
    r = client.post("/api/v1/payroll/runs", headers=HEADERS,
                    json={"period_id": PERIOD_ID, "jurisdiction": "IN", "currency": "INR"})
    assert r.status_code == 201, r.text


def test_create_non_in_run_keeps_its_own_currency():
    r = client.post("/api/v1/payroll/runs", headers=HEADERS,
                    json={"period_id": PERIOD_ID, "jurisdiction": "QQ", "currency": "USD"})
    assert r.status_code == 201, r.text
