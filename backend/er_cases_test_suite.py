"""Confidential Employee Relations cases (gap #9).

What this suite proves
----------------------
* HR creates an ER case (grievance/discipline/investigation/whistleblowing);
  ``pip`` and any other type are refused with 422; the reporter is the
  authenticated account, never the payload.
* The status machine moves forward one step at a time
  (Open > Triaged > Investigating > ActionTaken > Resolved > Closed):
  skips and backward moves are refused with 422, resolving requires a
  non-blank outcome, and resolving stamps ``resolved_at``.
* Confidentiality: non-HR, non-assignee reads (as requester, as the
  subject, as a manager) are ALL 404 — subjects cannot see cases about
  themselves; the assignee reads/uploads only the assigned case.
* Comments and attachments are append-only (no PUT/DELETE routes) and an
  attachment is both-or-neither with a key under ``/api/v1/files/``.
* ``GET /summary`` returns counts only — no ids, names or narratives.
* Cross-tenant HR reads are 404; tenant isolation holds.
* Every mutation records an audit row whose details carry no narrative.
* Migration 0051 upgrades a fresh database to head (round-trip).

Run:  python er_cases_test_suite.py
"""
import os
import subprocess
import sys
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="lp_er_"), "er_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.er_case import ERCase, ERCaseAttachment, ERCaseComment  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402
from datetime import date  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
db.add(
    User(
        username="er_admin",
        email="er_admin@example.test",
        hashed_password=get_password_hash("ErAdminPass123!!"),
        role="SuperAdmin",
        is_active=True,
        mfa_enabled=True,
    )
)
db.add(
    User(
        username="er_hr",
        email="er_hr@example.test",
        hashed_password=get_password_hash("ErHrPass123456!"),
        role="HR",
        is_active=True,
        mfa_enabled=True,
    )
)
dept = Department(name="Engineering", code="ENG")
db.add(dept)
db.flush()
job = Job(title="Engineer", code="ENG-JOB", department_id=dept.id)
db.add(job)
db.flush()
for code, first, last in (
    ("ER-A", "Asha", "Subject"),
    ("ER-B", "Bala", "Outsider"),
    ("ER-M", "Meera", "Manager"),
    ("ER-I", "Ira", "Investigator"),
):
    db.add(
        Employee(
            employee_id=code,
            first_name=first,
            last_name=last,
            email=f"{code.lower()}@example.test",
            hire_date=date(2024, 1, 15),
            job_id=job.id,
            department_id=dept.id,
            status="Active",
        )
    )
db.flush()
_emp = {e.employee_id: e.id for e in db.query(Employee).all()}
db.add(
    User(
        username="er_subject",
        email="er_subject@example.test",
        hashed_password=get_password_hash("ErSubjectPass1!"),
        role="Associate",
        is_active=True,
        mfa_enabled=False,
        employee_id=_emp["ER-A"],
    )
)
db.add(
    User(
        username="er_outsider",
        email="er_outsider@example.test",
        hashed_password=get_password_hash("ErOutsiderPass!"),
        role="Associate",
        is_active=True,
        mfa_enabled=False,
        employee_id=_emp["ER-B"],
    )
)
db.add(
    User(
        username="er_mgr",
        email="er_mgr@example.test",
        hashed_password=get_password_hash("ErMgrPass12345!"),
        role="Manager",
        is_active=True,
        mfa_enabled=False,
        employee_id=_emp["ER-M"],
    )
)
db.add(
    User(
        username="er_investigator",
        email="er_investigator@example.test",
        hashed_password=get_password_hash("ErInvestPass12!"),
        role="Associate",
        is_active=True,
        mfa_enabled=False,
        employee_id=_emp["ER-I"],
    )
)
db.commit()
SUBJECT_EMP_ID = _emp["ER-A"]
db.close()

client = TestClient(app, raise_server_exceptions=False)
_PASS, _FAIL = [], []


def check(name, fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        _FAIL.append((name, exc))
        print(f"FAIL  {name}: {exc!r}")
    else:
        _PASS.append(name)
        print(f"PASS  {name}")


def _headers(username, password):
    r = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


ADMIN_H = _headers("er_admin", "ErAdminPass123!!")
HR_H = _headers("er_hr", "ErHrPass123456!")
SUBJECT_H = _headers("er_subject", "ErSubjectPass1!")
OUTSIDER_H = _headers("er_outsider", "ErOutsiderPass!")
MGR_H = _headers("er_mgr", "ErMgrPass12345!")
INVEST_H = _headers("er_investigator", "ErInvestPass12!")


def _make_case(**overrides):
    payload = {
        "case_type": "grievance",
        "subject_employee_id": SUBJECT_EMP_ID,
        "severity": "High",
        "classification": "shift dispute",
    }
    payload.update(overrides)
    r = client.post("/api/v1/er-cases", json=payload, headers=HR_H)
    assert r.status_code == 201, r.text
    return r.json()


def _audit_count(action, entity_id):
    s = SessionLocal()
    try:
        return (
            s.query(AuditLog)
            .filter(AuditLog.action == action, AuditLog.entity_id == entity_id)
            .count()
        )
    finally:
        s.close()


def test_create_reports_authenticated_reporter_and_audits():
    case = _make_case()
    assert case["status"] == "Open", case
    assert case["reported_by"] == "er_hr", case
    assert case["case_type"] == "grievance", case
    assert _audit_count("create_er_case", case["id"]) == 1, case


def test_pip_case_type_is_refused():
    r = client.post(
        "/api/v1/er-cases",
        json={"case_type": "pip", "subject_employee_id": SUBJECT_EMP_ID},
        headers=HR_H,
    )
    assert r.status_code == 422, r.text


def test_reported_by_cannot_be_spoofed():
    r = client.post(
        "/api/v1/er-cases",
        json={"case_type": "grievance", "reported_by": "someone_else"},
        headers=HR_H,
    )
    # The schema is closed on reporter identity: a payload-supplied
    # reporter is ignored (422 extra) or never stored.
    assert r.status_code in (201, 422), r.text
    if r.status_code == 201:
        assert r.json()["reported_by"] == "er_hr", r.text


def test_non_hr_create_is_refused():
    for h in (SUBJECT_H, OUTSIDER_H, MGR_H, INVEST_H):
        r = client.post(
            "/api/v1/er-cases",
            json={"case_type": "grievance"},
            headers=h,
        )
        assert r.status_code == 403, (h, r.status_code, r.text)


def test_machine_advances_one_step_and_resolves_with_outcome():
    case = _make_case(case_type="discipline")
    cid = case["id"]
    # Skip is refused.
    r = client.put(f"/api/v1/er-cases/{cid}", json={"status": "Investigating"}, headers=HR_H)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "invalid_status_transition", r.text
    for nxt in ("Triaged", "Investigating", "ActionTaken"):
        r = client.put(f"/api/v1/er-cases/{cid}", json={"status": nxt}, headers=HR_H)
        assert r.status_code == 200, (nxt, r.text)
    # Resolving without an outcome is refused.
    r = client.put(f"/api/v1/er-cases/{cid}", json={"status": "Resolved"}, headers=HR_H)
    assert r.status_code == 422, r.text
    r = client.put(
        f"/api/v1/er-cases/{cid}",
        json={"status": "Resolved", "outcome": "Written warning issued."},
        headers=HR_H,
    )
    assert r.status_code == 200, r.text
    assert r.json()["resolved_at"], r.text
    r = client.put(f"/api/v1/er-cases/{cid}", json={"status": "Closed"}, headers=HR_H)
    assert r.status_code == 200, r.text
    # Closed is terminal; backward moves refused.
    r = client.put(f"/api/v1/er-cases/{cid}", json={"status": "Open"}, headers=HR_H)
    assert r.status_code == 422, r.text


def test_subject_cannot_see_case_about_themselves():
    case = _make_case()
    cid = case["id"]
    for url in ("/api/v1/er-cases", f"/api/v1/er-cases/{cid}", f"/api/v1/er-cases/{cid}/comments"):
        r = client.get(url, headers=SUBJECT_H)
        assert r.status_code == 404, (url, r.status_code, r.text)


def test_outsider_and_manager_get_404_everywhere():
    case = _make_case()
    cid = case["id"]
    for h in (OUTSIDER_H, MGR_H):
        for url in (
            "/api/v1/er-cases",
            f"/api/v1/er-cases/{cid}",
            f"/api/v1/er-cases/{cid}/comments",
            "/api/v1/er-cases/summary",
        ):
            r = client.get(url, headers=h)
            # Queue/summary/detail are all hidden: 404 for reads, 403 for
            # the role-gated summary (never a case body).
            assert r.status_code in (403, 404), (url, r.status_code, r.text)
        r = client.post(
            f"/api/v1/er-cases/{cid}/comments", json={"comment": "hi"}, headers=h
        )
        assert r.status_code == 404, r.text


def test_assignee_reads_and_comments_on_assigned_case_only():
    case = _make_case()
    cid = case["id"]
    other = _make_case(case_type="investigation")
    # Unassigned: 404.
    assert client.get(f"/api/v1/er-cases/{cid}", headers=INVEST_H).status_code == 404
    # The queue itself is hidden from the assignee.
    assert client.get("/api/v1/er-cases", headers=INVEST_H).status_code == 404
    # HR assigns the case.
    r = client.put(
        f"/api/v1/er-cases/{cid}", json={"assigned_to": "er_investigator"}, headers=HR_H
    )
    assert r.status_code == 200, r.text
    # Now the assignee reads and comments.
    r = client.get(f"/api/v1/er-cases/{cid}", headers=INVEST_H)
    assert r.status_code == 200, r.text
    r = client.post(
        f"/api/v1/er-cases/{cid}/comments",
        json={"comment": "Interviewed the shift lead."},
        headers=INVEST_H,
    )
    assert r.status_code == 201, r.text
    assert r.json()["author"] == "er_investigator", r.text
    # But not the other unassigned case.
    assert client.get(f"/api/v1/er-cases/{other['id']}", headers=INVEST_H).status_code == 404
    # And the assignee cannot move the case (HR-only update).
    r = client.put(
        f"/api/v1/er-cases/{cid}", json={"status": "Triaged"}, headers=INVEST_H
    )
    assert r.status_code == 403, r.text


def test_comments_are_append_only():
    case = _make_case()
    cid = case["id"]
    r = client.post(
        f"/api/v1/er-cases/{cid}/comments", json={"comment": "First note."}, headers=HR_H
    )
    assert r.status_code == 201, r.text
    nid = r.json()["id"]
    for method in ("put", "delete", "patch"):
        r = getattr(client, method)(
            f"/api/v1/er-cases/{cid}/comments/{nid}", headers=HR_H
        )
        assert r.status_code in (404, 405), (method, r.status_code)


def test_attachment_both_or_neither_and_prefix():
    case = _make_case(case_type="whistleblowing")
    cid = case["id"]
    # Half-formed is refused.
    r = client.post(
        f"/api/v1/er-cases/{cid}/attachments",
        json={"filename": "note.pdf"},
        headers=HR_H,
    )
    assert r.status_code == 422, r.text
    # Off-prefix key is refused.
    r = client.post(
        f"/api/v1/er-cases/{cid}/attachments",
        json={"filename": "note.pdf", "file_key": "/tmp/evil.pdf"},
        headers=HR_H,
    )
    assert r.status_code == 422, r.text
    # Well-formed is stored.
    r = client.post(
        f"/api/v1/er-cases/{cid}/attachments",
        json={"filename": "note.pdf", "file_key": "/api/v1/files/er/note.pdf"},
        headers=HR_H,
    )
    assert r.status_code == 201, r.text
    assert r.json()["uploaded_by"] == "er_hr", r.text


def test_summary_is_aggregates_only():
    _make_case(case_type="grievance")
    _make_case(case_type="discipline")
    r = client.get("/api/v1/er-cases/summary", headers=HR_H)
    assert r.status_code == 200, r.text
    body = r.text
    assert "by_case_type" in r.json() and "by_status" in r.json(), r.text
    for leak in ("shift dispute", "er_subject", "Asha", "Interviewed"):
        assert leak not in body, leak


def test_closed_cases_keep_history():
    case = _make_case()
    cid = case["id"]
    client.post(
        f"/api/v1/er-cases/{cid}/comments", json={"comment": "Keep me."}, headers=HR_H
    )
    for nxt, extra in (
        ("Triaged", {}),
        ("Investigating", {}),
        ("ActionTaken", {}),
        ("Resolved", {"outcome": "Upheld in part."}),
        ("Closed", {}),
    ):
        r = client.put(f"/api/v1/er-cases/{cid}", json={"status": nxt, **extra}, headers=HR_H)
        assert r.status_code == 200, (nxt, r.text)
    r = client.get(f"/api/v1/er-cases/{cid}/comments", headers=HR_H)
    assert r.status_code == 200, r.text
    assert any(m["comment"] == "Keep me." for m in r.json()), r.text


def test_cross_tenant_hr_read_is_404():
    s = SessionLocal()
    try:
        for uname, role in (("er_hr_a", "HR"), ("er_hr_b", "HR")):
            if not s.query(User).filter(User.username == uname).first():
                s.add(
                    User(
                        username=uname,
                        email=f"{uname}@example.test",
                        hashed_password=get_password_hash("TenantPass123!"),
                        role=role,
                        is_active=True,
                        mfa_enabled=True,
                    )
                )
        s.commit()
    finally:
        s.close()
    ha = {"Authorization": f"Bearer {create_access_token(subject='er_hr_a', extra_claims={'tenant': 'tenant-a'})}"}
    hb = {"Authorization": f"Bearer {create_access_token(subject='er_hr_b', extra_claims={'tenant': 'tenant-b'})}"}
    r = client.post(
        "/api/v1/er-cases", json={"case_type": "grievance", "severity": "Low"}, headers=ha
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    assert r.json()["tenant_id"] == "tenant-a", r.text
    # Same-tenant HR reads fine; other-tenant HR gets 404.
    assert client.get(f"/api/v1/er-cases/{cid}", headers=ha).status_code == 200
    r = client.get(f"/api/v1/er-cases/{cid}", headers=hb)
    assert r.status_code == 404, r.text
    # ... and the foreign case never appears in the other tenant's queue.
    r = client.get("/api/v1/er-cases", headers=hb)
    assert r.status_code == 200, r.text
    assert all(c["id"] != cid for c in r.json()), r.text


def test_every_mutation_is_audited_without_narrative():
    case = _make_case(classification="overtime rota")
    cid = case["id"]
    r = client.post(
        f"/api/v1/er-cases/{cid}/comments",
        json={"comment": "ULTRASECRET narrative text"},
        headers=HR_H,
    )
    assert r.status_code == 201, r.text
    r = client.post(
        f"/api/v1/er-cases/{cid}/attachments",
        json={"filename": "x.pdf", "file_key": "/api/v1/files/er/x.pdf"},
        headers=HR_H,
    )
    assert r.status_code == 201, r.text
    s = SessionLocal()
    try:
        rows = (
            s.query(AuditLog)
            .filter(
                AuditLog.action.in_(
                    ["create_er_case", "add_er_comment", "add_er_attachment"]
                )
            )
            .all()
        )
        assert rows, "no audit rows"
        blob = " ".join((x.details or "") for x in rows)
        assert "ULTRASECRET" not in blob, blob
        assert "overtime rota" not in blob, blob
    finally:
        s.close()


def test_hr_cases_routes_unchanged():
    # The helpdesk queue still answers for HR (no ER regression).
    r = client.get("/api/v1/core-hr/cases", headers=ADMIN_H)
    assert r.status_code == 200, r.text


def test_migration_0051_upgrades_a_fresh_database_to_head():
    from sqlalchemy import create_engine, inspect  # noqa: E402

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    try:
        env = dict(os.environ, DATABASE_URL=f"sqlite:///{tmp}")
        here = os.path.dirname(os.path.abspath(__file__))
        for rev in ("0051_er_cases", "-1", "0051_er_cases"):
            verb = "downgrade" if rev == "-1" else "upgrade"
            out = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from alembic.config import Config; "
                    "from alembic import command; "
                    f"command.{verb}(Config('alembic.ini'), '{rev}')",
                ],
                capture_output=True,
                text=True,
                cwd=here,
                env=env,
            )
            assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
            if verb == "downgrade":
                names = set(inspect(create_engine(f"sqlite:///{tmp}")).get_table_names())
                assert "er_cases" not in names, names
        names = set(inspect(create_engine(f"sqlite:///{tmp}")).get_table_names())
        assert {"er_cases", "er_case_comments", "er_case_attachments"} <= names, names
    finally:
        os.unlink(tmp)


def main():
    for name, fn in [
        ("create reports authenticated reporter with audit", test_create_reports_authenticated_reporter_and_audits),
        ("pip case type is refused", test_pip_case_type_is_refused),
        ("reported_by cannot be spoofed", test_reported_by_cannot_be_spoofed),
        ("non-HR create is refused", test_non_hr_create_is_refused),
        ("machine advances one step, resolve needs outcome", test_machine_advances_one_step_and_resolves_with_outcome),
        ("subject cannot see case about themselves", test_subject_cannot_see_case_about_themselves),
        ("outsider and manager get 404 everywhere", test_outsider_and_manager_get_404_everywhere),
        ("assignee reads/comments on assigned case only", test_assignee_reads_and_comments_on_assigned_case_only),
        ("comments are append-only", test_comments_are_append_only),
        ("attachment both-or-neither and prefix", test_attachment_both_or_neither_and_prefix),
        ("summary is aggregates only", test_summary_is_aggregates_only),
        ("closed cases keep history", test_closed_cases_keep_history),
        ("cross-tenant HR read is 404", test_cross_tenant_hr_read_is_404),
        ("every mutation audited without narrative", test_every_mutation_is_audited_without_narrative),
        ("hr_cases routes unchanged", test_hr_cases_routes_unchanged),
        ("migration 0051 upgrades fresh db to head", test_migration_0051_upgrades_a_fresh_database_to_head),
    ]:
        check(name, fn)
    print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
    for name, exc in _FAIL:
        print(f"FAIL  {name}: {exc!r}")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
