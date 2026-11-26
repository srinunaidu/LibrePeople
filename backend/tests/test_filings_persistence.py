"""Filing persistence (filing-persistence).

Proves, against the served API:
* POST /reports/filings/{type}/records?period= persists the generated
  content-hash and returns 201 with version=1; a repeat identical POST is
  a 409 duplicate (AC1);
* GET /reports/filings/records?type=&period=&status= lists records with
  submission history, newest-first (AC2);
* submit|accept|reject enforce only legal transitions; an illegal move is
  422 and writes no audit row (AC3);
* resubmission opens version N+1 linked to the prior id; the original row's
  content is immutable (AC4);
* unauthenticated requests are 401; Manager/Associate are 403 while
  PayrollViewer (and up) may write (AC5);
* the generated txt download is unchanged (regression).

Run:  python tests/test_filings_persistence.py   (from backend/)
  or: pytest tests/test_filings_persistence.py -q
"""
import datetime
import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

DB_DIR = tempfile.mkdtemp(prefix="filings_persist_suite_")
DB_PATH = os.path.join(DB_DIR, "filings_persist_suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test"
os.environ["RULE_PACK_DIR"] = os.path.join(str(_BACKEND_ROOT), "rule_packs")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.filing_record import FilingRecord  # noqa: E402
from app.models.user import User  # noqa: E402

TENANT = "tenant-fil-a"
PASSWORD = "FilingsPersist123"

_RESULT = None

PERIOD_A = "2025-10"  # inside the verified IN pack (FY25-26)
PERIOD_B = "2025-11"


def _run() -> dict:
    global _RESULT
    if _RESULT is not None:
        return _RESULT

    results = {"pass": 0, "fail": 0}
    failures: list[tuple[str, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        if ok:
            results["pass"] += 1
            print(f"  PASS  {name}")
        else:
            results["fail"] += 1
            failures.append((name, detail))
            print(f"  FAIL  {name}  {detail}")

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    def _user(username: str, role: str) -> None:
        if db.query(User).filter(User.username == username).first() is None:
            db.add(User(
                username=username, email=f"{username}@example.com",
                hashed_password=get_password_hash(PASSWORD),
                role=role, is_active=True,
                mfa_enabled=role in ("SuperAdmin", "HR"),
            ))
            db.commit()

    _user("fil_admin", "SuperAdmin")
    _user("fil_hr", "HR")
    _user("fil_mgr", "Manager")
    _user("fil_assoc", "Associate")
    _user("fil_pay", "PayrollViewer")
    db.close()

    client = TestClient(app, raise_server_exceptions=False)

    def _headers(username: str, tenant: str = TENANT) -> dict:
        token = create_access_token(subject=username, extra_claims={"tenant": tenant})
        return {"Authorization": f"Bearer {token}"}

    H_ADMIN = _headers("fil_admin")
    H_HR = _headers("fil_hr")
    H_MGR = _headers("fil_mgr")
    H_ASSOC = _headers("fil_assoc")
    H_PAY = _headers("fil_pay")

    def _audit_count() -> int:
        s = SessionLocal()
        try:
            return s.query(AuditLog).filter(AuditLog.entity_type == "FilingRecord").count()
        finally:
            s.close()

    # =====================================================================
    print("\n[FIL-0] Auth: 401 anonymous, 403 wrong role (AC5)")
    # =====================================================================
    r = client.get("/api/v1/reports/filings/records")
    check("unauthenticated list is 401", r.status_code == 401, f"got {r.status_code}: {r.text[:200]}")
    r = client.post(f"/api/v1/reports/filings/pf_ecr/records?period={PERIOD_A}")
    check("unauthenticated create is 401", r.status_code == 401, f"got {r.status_code}: {r.text[:200]}")
    r = client.post(f"/api/v1/reports/filings/pf_ecr/records?period={PERIOD_A}", headers=H_MGR)
    check("Manager create is 403", r.status_code == 403, f"got {r.status_code}: {r.text[:200]}")
    r = client.get("/api/v1/reports/filings/records", headers=H_ASSOC)
    check("Associate list is 403", r.status_code == 403, f"got {r.status_code}: {r.text[:200]}")

    # =====================================================================
    print("\n[FIL-1] Create persists hash, version=1; repeat is 409 (AC1)")
    # =====================================================================
    before_audit = _audit_count()
    r = client.post(f"/api/v1/reports/filings/pf_ecr/records?period={PERIOD_A}", headers=H_PAY)
    check("PayrollViewer create is 201", r.status_code == 201, f"got {r.status_code}: {r.text[:300]}")
    body = r.json()
    check("version is 1", body.get("version") == 1, r.text[:300])
    check("status is Draft", body.get("status") == "Draft", r.text[:300])
    check("content_hash is sha256 hex", len(body.get("content_hash") or "") == 64, r.text[:300])
    check("audit row written on create", _audit_count() == before_audit + 1, f"count={_audit_count()}")
    V1 = body.get("id")
    HASH_V1 = body.get("content_hash")

    # The saved hash must equal what the untouched download streams.
    g = client.get(f"/api/v1/reports/filings/pf_ecr?period={PERIOD_A}", headers=H_PAY)
    check("download still streams txt", g.status_code == 200 and "text/plain" in g.headers.get("content-type", ""), f"got {g.status_code}")
    check(
        "record hashes exactly the streamed bytes",
        hashlib.sha256(g.content).hexdigest() == HASH_V1,
        f"record={HASH_V1} stream={hashlib.sha256(g.content).hexdigest()}",
    )

    r = client.post(f"/api/v1/reports/filings/pf_ecr/records?period={PERIOD_A}", headers=H_PAY)
    check("identical repeat POST is 409", r.status_code == 409, f"got {r.status_code}: {r.text[:300]}")
    check("duplicate wrote no audit row", _audit_count() == before_audit + 1, f"count={_audit_count()}")

    # Alias normalises to canonical: 24q → 24q_quarterly.
    r = client.post(f"/api/v1/reports/filings/24q/records?period={PERIOD_A}", headers=H_HR)
    check("alias create is 201", r.status_code == 201, f"got {r.status_code}: {r.text[:300]}")
    check("alias stored canonical", r.json().get("filing_type") == "24q_quarterly", r.text[:300])
    V_24Q = r.json().get("id")

    r = client.post("/api/v1/reports/filings/bogus/records?period=2025-10", headers=H_HR)
    check("unknown filing type is 422", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")
    r = client.post(f"/api/v1/reports/filings/pt_challan/records?period={PERIOD_A}&state=DL", headers=H_HR)
    check("invalid PT state is 422", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")

    # =====================================================================
    print("\n[FIL-2] List with history, newest-first, filters (AC2)")
    # =====================================================================
    r = client.post(f"/api/v1/reports/filings/esi_return/records?period={PERIOD_B}", headers=H_HR)
    check("second-period create is 201", r.status_code == 201, f"got {r.status_code}: {r.text[:300]}")
    V_ESI = r.json().get("id")

    r = client.get("/api/v1/reports/filings/records", headers=H_PAY)
    check("list is 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    records = r.json().get("records", [])
    ids = [rec["id"] for rec in records]
    check("newest-first order", ids == sorted(ids, reverse=True), f"ids={ids}")
    check("every record carries history", all(isinstance(rec.get("history"), list) for rec in records), r.text[:200])
    v1 = next(rec for rec in records if rec["id"] == V1)
    check("history holds the creation audit", any(h["action"] == "filing_record_created" for h in v1["history"]), str(v1["history"])[:300])

    r = client.get(f"/api/v1/reports/filings/records?type=pf_ecr&period={PERIOD_A}", headers=H_PAY)
    check("type+period filter hits one row", r.json().get("count") == 1 and r.json()["records"][0]["id"] == V1, r.text[:300])
    r = client.get("/api/v1/reports/filings/records?status=Draft", headers=H_PAY)
    check("status filter returns drafts", r.json().get("count") >= 3, r.text[:300])
    r = client.get("/api/v1/reports/filings/records?status=Bogus", headers=H_PAY)
    check("unknown status filter is 422", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")

    # =====================================================================
    print("\n[FIL-3] Transition matrix; illegal is 422 with no audit (AC3)")
    # =====================================================================
    before_audit = _audit_count()
    r = client.post(f"/api/v1/reports/filings/records/{V1}/accept", headers=H_PAY)
    check("accept from Draft is 422", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")
    check("illegal move wrote no audit row", _audit_count() == before_audit, f"count={_audit_count()}")
    r = client.post(f"/api/v1/reports/filings/records/{V1}/bogusaction", headers=H_PAY)
    check("unknown action is 422", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")
    r = client.post("/api/v1/reports/filings/records/999999/submit", headers=H_PAY)
    check("unknown id is 404", r.status_code == 404, f"got {r.status_code}: {r.text[:200]}")

    r = client.post(f"/api/v1/reports/filings/records/{V1}/submit", headers=H_MGR)
    check("Manager transition is 403", r.status_code == 403, f"got {r.status_code}: {r.text[:200]}")
    r = client.post(f"/api/v1/reports/filings/records/{V1}/submit", headers=H_PAY)
    check("submit Draft→Submitted", r.status_code == 200 and r.json().get("status") == "Submitted", f"got {r.status_code}: {r.text[:300]}")
    check("submitted_by stamped", r.json().get("submitted_by") is not None and r.json().get("submitted_at") is not None, r.text[:300])
    check("submit audited", any(h["action"] == "filing_record_submitted" for h in r.json().get("history", [])), r.text[:300])

    r = client.post(f"/api/v1/reports/filings/records/{V1}/submit", headers=H_PAY)
    check("re-submit is 422", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")
    r = client.post(f"/api/v1/reports/filings/records/{V1}/accept", headers=H_HR)
    check("accept Submitted→Accepted", r.status_code == 200 and r.json().get("status") == "Accepted", f"got {r.status_code}: {r.text[:300]}")
    r = client.post(f"/api/v1/reports/filings/records/{V1}/reject", headers=H_HR)
    check("reject after Accepted is 422", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")
    r = client.post(f"/api/v1/reports/filings/records/{V1}/resubmit", headers=H_HR)
    check("resubmit of Accepted is 422", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")

    # =====================================================================
    print("\n[FIL-4] Resubmission versions; original immutable (AC4)")
    # =====================================================================
    r = client.post(f"/api/v1/reports/filings/records/{V_24Q}/submit", headers=H_PAY)
    check("24q submits", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    r = client.post(f"/api/v1/reports/filings/records/{V_24Q}/reject", headers=H_HR)
    check("24q rejects", r.status_code == 200 and r.json().get("status") == "Rejected", f"got {r.status_code}: {r.text[:300]}")

    s = SessionLocal()
    old_hash = s.query(FilingRecord).filter(FilingRecord.id == V_24Q).first().content_hash
    old_version = s.query(FilingRecord).filter(FilingRecord.id == V_24Q).first().version
    s.close()

    r = client.post(f"/api/v1/reports/filings/records/{V_24Q}/resubmit", headers=H_PAY)
    check("resubmit is 200", r.status_code == 200, f"got {r.status_code}: {r.text[:300]}")
    new_body = r.json()
    check("new version is N+1", new_body.get("version") == old_version + 1, r.text[:300])
    check("new row links supersedes_id", new_body.get("supersedes_id") == V_24Q, r.text[:300])
    check("new row is Draft", new_body.get("status") == "Draft", r.text[:300])
    V2 = new_body.get("id")
    check("resubmit audited on both rows",
          any(h["action"] == "filing_record_created" for h in new_body.get("history", [])), r.text[:300])

    s = SessionLocal()
    old = s.query(FilingRecord).filter(FilingRecord.id == V_24Q).first()
    check("original row content-hash untouched", old.content_hash == old_hash, f"{old.content_hash} vs {old_hash}")
    check("original row now Resubmitted", old.status == "Resubmitted", f"status={old.status}")
    check("original version unchanged", old.version == old_version, f"version={old.version}")
    s.close()

    r = client.get("/api/v1/reports/filings/records?status=Resubmitted", headers=H_PAY)
    check("old row lists under Resubmitted", any(rec["id"] == V_24Q for rec in r.json().get("records", [])), r.text[:300])
    r = client.post(f"/api/v1/reports/filings/records/{V_24Q}/submit", headers=H_PAY)
    check("terminal Resubmitted row rejects moves", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")

    # The new Draft version walks the normal path again.
    r = client.post(f"/api/v1/reports/filings/records/{V2}/submit", headers=H_PAY)
    check("resubmitted version submits", r.status_code == 200 and r.json().get("status") == "Submitted", f"got {r.status_code}: {r.text[:300]}")

    # =====================================================================
    print("\n[FIL-5] Audit trail covers every transition")
    # =====================================================================
    s = SessionLocal()
    try:
        actions = sorted(
            a.action
            for a in s.query(AuditLog).filter(
                AuditLog.entity_type == "FilingRecord", AuditLog.entity_id == V_24Q
            ).all()
        )
    finally:
        s.close()
    for expected in ("filing_record_created", "filing_record_submitted", "filing_record_rejected", "filing_record_resubmitted"):
        check(f"audit holds {expected}", expected in actions, f"actions={actions}")

    _RESULT = {"pass": results["pass"], "fail": results["fail"], "failures": failures}
    print(f"\nfilings_persistence: {results['pass']} passed, {results['fail']} failed")
    return _RESULT


def test_filings_persistence() -> None:
    result = _run()
    assert result["fail"] == 0, f"failures: {result['failures']}"


if __name__ == "__main__":
    result = _run()
    shutil.rmtree(DB_DIR, ignore_errors=True)
    raise SystemExit(1 if result["fail"] else 0)
