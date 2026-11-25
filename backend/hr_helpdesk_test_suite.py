"""HR helpdesk cases and comments (LP-SVC-001+003).

What this suite proves
----------------------
* Creating a case defaults to ``Open`` and records an audit row; a bad
  category, priority or status is refused with 422 (closed Literal enums).
* The status machine moves forward one step at a time
  (Open > InProgress > Resolved > Closed): skips and backward moves are
  refused with 422, resolving requires a non-blank resolution, and
  resolving stamps ``resolved_at``.
* Comments are append-only: there is no update or delete route for them.
* A comment attachment is both-or-neither (filename + key) and the key
  must live under the authorised ``/api/v1/files/`` prefix.
* Visibility is participant-only: HR sees every case, anyone else sees
  only cases about themselves or assigned to them — anything else is 404,
  and the list endpoints filter the same way.
* Every mutation (create, status change, comment) records an audit row.
* Migration ``0041_case_comment_attachments`` upgrades a fresh database
  to head.

Run:  python hr_helpdesk_test_suite.py
"""
import os
import subprocess
import sys
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="lp_svc_"), "svc_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, inspect  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.core_hr import CaseComment, HRCase  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402
from datetime import date  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
db.add(
    User(
        username="svc_admin",
        email="svc_admin@example.test",
        hashed_password=get_password_hash("SvcAdminPass123!"),
        role="SuperAdmin",
        is_active=True,
        mfa_enabled=True,
    )
)
db.add(
    User(
        username="svc_hr",
        email="svc_hr@example.test",
        hashed_password=get_password_hash("SvcHrPass12345!"),
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
    ("SVC-A", "Asha", "Owner"),
    ("SVC-B", "Bala", "Outsider"),
    ("SVC-M", "Meera", "Manager"),
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
        username="svc_owner",
        email="svc_owner@example.test",
        hashed_password=get_password_hash("SvcOwnerPass123!"),
        role="Associate",
        is_active=True,
        mfa_enabled=False,
        employee_id=_emp["SVC-A"],
    )
)
db.add(
    User(
        username="svc_outsider",
        email="svc_outsider@example.test",
        hashed_password=get_password_hash("SvcOutsiderPass123!"),
        role="Associate",
        is_active=True,
        mfa_enabled=False,
        employee_id=_emp["SVC-B"],
    )
)
db.add(
    User(
        username="svc_mgr",
        email="svc_mgr@example.test",
        hashed_password=get_password_hash("SvcMgrPass12345!"),
        role="Manager",
        is_active=True,
        mfa_enabled=False,
        employee_id=_emp["SVC-M"],
    )
)
db.add(
    User(
        username="svc_nolink",
        email="svc_nolink@example.test",
        hashed_password=get_password_hash("SvcNoLinkPass123!"),
        role="Associate",
        is_active=True,
        mfa_enabled=False,
        employee_id=None,
    )
)
db.commit()
OWNER_EMP_ID = _emp["SVC-A"]
OUTSIDER_EMP_ID = _emp["SVC-B"]
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


ADMIN_H = _headers("svc_admin", "SvcAdminPass123!")
HR_H = _headers("svc_hr", "SvcHrPass12345!")
OWNER_H = _headers("svc_owner", "SvcOwnerPass123!")
OUTSIDER_H = _headers("svc_outsider", "SvcOutsiderPass123!")
MGR_H = _headers("svc_mgr", "SvcMgrPass12345!")
NOLINK_H = _headers("svc_nolink", "SvcNoLinkPass123!")


def _make_case(**overrides):
    payload = {
        "employee_id": OWNER_EMP_ID,
        "subject": "Payroll correction for March",
        "category": "Payroll",
        "priority": "High",
        "assigned_to": "svc_mgr",
    }
    payload.update(overrides)
    r = client.post("/api/v1/core-hr/cases", json=payload, headers=ADMIN_H)
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


def test_create_defaults_to_open_with_audit():
    case = _make_case()
    assert case["status"] == "Open", case
    assert case["category"] == "Payroll", case
    assert case["priority"] == "High", case
    assert _audit_count("create_hr_case", case["id"]) == 1, case


def test_associate_creates_own_case_forced_to_self():
    # No employee_id in the payload: the endpoint must still bind the case
    # to the associate's own employee record (LP-SVC-003). Routing and SLA
    # are the helpdesk's to set, so an associate asking for a colleague's
    # queue, a fabricated deadline or an escalated priority is overruled.
    r = client.post(
        "/api/v1/core-hr/cases",
        json={
            "subject": "I need a payslip copy",
            "category": "Payroll",
            "assigned_to": "svc_mgr",
            "sla_due": "2020-01-01T00:00:00",
            "priority": "Urgent",
        },
        headers=OWNER_H,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["employee_id"] == OWNER_EMP_ID, body
    assert body["status"] == "Open", body
    assert body["assigned_to"] is None, body
    assert body["sla_due"] is None, body
    assert body["priority"] == "Medium", body


def test_associate_without_employee_link_cannot_create_case():
    r = client.post(
        "/api/v1/core-hr/cases",
        json={"subject": "No employee record", "category": "General"},
        headers=NOLINK_H,
    )
    assert r.status_code == 403, r.text


def test_associate_cannot_create_case_about_colleague():
    r = client.post(
        "/api/v1/core-hr/cases",
        json={"employee_id": OUTSIDER_EMP_ID, "subject": "Not mine", "category": "General"},
        headers=OWNER_H,
    )
    assert r.status_code == 403, r.text


def test_hr_creates_case_for_any_employee():
    r = client.post(
        "/api/v1/core-hr/cases",
        json={"employee_id": OUTSIDER_EMP_ID, "subject": "Raised by HR", "category": "General"},
        headers=HR_H,
    )
    assert r.status_code == 201, r.text
    assert r.json()["employee_id"] == OUTSIDER_EMP_ID, r.json()


def test_associate_comments_on_own_case():
    case = _make_case()
    r = client.post(
        f"/api/v1/core-hr/cases/{case['id']}/comments",
        json={"case_id": case["id"], "author": "svc_owner", "comment": "Adding context."},
        headers=OWNER_H,
    )
    assert r.status_code == 201, r.text


def test_associate_comment_on_another_case_is_404():
    case = _make_case(subject="A colleague's case")
    r = client.post(
        f"/api/v1/core-hr/cases/{case['id']}/comments",
        json={"case_id": case["id"], "author": "svc_outsider", "comment": "Nosy."},
        headers=OUTSIDER_H,
    )
    assert r.status_code == 404, r.text


def test_bad_category_is_refused():
    r = client.post(
        "/api/v1/core-hr/cases",
        json={"employee_id": OWNER_EMP_ID, "subject": "x", "category": "Nope"},
        headers=ADMIN_H,
    )
    assert r.status_code == 422, r.text


def test_bad_priority_is_refused():
    r = client.post(
        "/api/v1/core-hr/cases",
        json={"employee_id": OWNER_EMP_ID, "subject": "x", "priority": "ASAP"},
        headers=ADMIN_H,
    )
    assert r.status_code == 422, r.text


def test_open_moves_to_in_progress():
    case = _make_case()
    r = client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"status": "InProgress"}, headers=HR_H
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "InProgress", r.text
    assert _audit_count("update_hr_case", case["id"]) >= 1


def test_open_cannot_skip_to_resolved():
    case = _make_case()
    r = client.put(
        f"/api/v1/core-hr/cases/{case['id']}",
        json={"status": "Resolved", "resolution": "done"},
        headers=HR_H,
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "invalid_status_transition", r.text


def test_resolve_requires_a_resolution():
    case = _make_case()
    r = client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"status": "InProgress"}, headers=HR_H
    )
    assert r.status_code == 200, r.text
    r = client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"status": "Resolved"}, headers=HR_H
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "resolution_required", r.text


def test_resolve_with_resolution_stamps_resolved_at():
    case = _make_case()
    r = client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"status": "InProgress"}, headers=HR_H
    )
    assert r.status_code == 200, r.text
    assert r.json()["resolved_at"] is None, r.text
    r = client.put(
        f"/api/v1/core-hr/cases/{case['id']}",
        json={"status": "Resolved", "resolution": "Corrected in the March run."},
        headers=HR_H,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "Resolved", body
    assert body["resolution"] == "Corrected in the March run.", body
    assert body["resolved_at"], body


def test_resolved_moves_to_closed():
    case = _make_case()
    client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"status": "InProgress"}, headers=HR_H
    )
    client.put(
        f"/api/v1/core-hr/cases/{case['id']}",
        json={"status": "Resolved", "resolution": "Fixed."},
        headers=HR_H,
    )
    r = client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"status": "Closed"}, headers=HR_H
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "Closed", r.text


def test_closed_is_terminal():
    case = _make_case()
    client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"status": "InProgress"}, headers=HR_H
    )
    client.put(
        f"/api/v1/core-hr/cases/{case['id']}",
        json={"status": "Resolved", "resolution": "Fixed."},
        headers=HR_H,
    )
    client.put(f"/api/v1/core-hr/cases/{case['id']}", json={"status": "Closed"}, headers=HR_H)
    r = client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"status": "InProgress"}, headers=HR_H
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "invalid_status_transition", r.text


def test_backward_move_is_refused():
    case = _make_case()
    client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"status": "InProgress"}, headers=HR_H
    )
    client.put(
        f"/api/v1/core-hr/cases/{case['id']}",
        json={"status": "Resolved", "resolution": "Fixed."},
        headers=HR_H,
    )
    r = client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"status": "InProgress"}, headers=HR_H
    )
    assert r.status_code == 422, r.text


def test_bad_status_literal_is_refused():
    case = _make_case()
    r = client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"status": "In Progress"}, headers=HR_H
    )
    assert r.status_code == 422, r.text


def test_field_update_without_status_change_is_allowed():
    case = _make_case()
    r = client.put(
        f"/api/v1/core-hr/cases/{case['id']}",
        json={"subject": "Payroll correction for April"},
        headers=HR_H,
    )
    assert r.status_code == 200, r.text
    assert r.json()["subject"] == "Payroll correction for April", r.text
    assert r.json()["status"] == "Open", r.text


def test_blank_resolution_is_refused():
    case = _make_case()
    client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"status": "InProgress"}, headers=HR_H
    )
    r = client.put(
        f"/api/v1/core-hr/cases/{case['id']}",
        json={"status": "Resolved", "resolution": "   "},
        headers=HR_H,
    )
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "resolution_required", r.text


def test_comments_are_append_only():
    case = _make_case()
    r = client.post(
        f"/api/v1/core-hr/cases/{case['id']}/comments",
        json={"case_id": case["id"], "author": "svc_hr", "comment": "Looking into it."},
        headers=HR_H,
    )
    assert r.status_code == 201, r.text
    comment_id = r.json()["id"]
    for method in ("put", "patch", "delete"):
        r = client.request(method, f"/api/v1/core-hr/cases/comments/{comment_id}")
        assert r.status_code in (404, 405), (method, r.status_code, r.text)
    s = SessionLocal()
    try:
        assert s.query(CaseComment).filter(CaseComment.id == comment_id).count() == 1
    finally:
        s.close()


def test_owner_can_comment_but_outsider_gets_404():
    case = _make_case()
    r = client.post(
        f"/api/v1/core-hr/cases/{case['id']}/comments",
        json={"case_id": case["id"], "author": "svc_owner", "comment": "Any update?"},
        headers=OWNER_H,
    )
    assert r.status_code == 201, r.text
    assert _audit_count("add_case_comment", r.json()["id"]) == 1
    r = client.post(
        f"/api/v1/core-hr/cases/{case['id']}/comments",
        json={"case_id": case["id"], "author": "svc_outsider", "comment": "Nosy."},
        headers=OUTSIDER_H,
    )
    assert r.status_code == 404, r.text
    s = SessionLocal()
    try:
        assert (
            s.query(CaseComment)
            .filter(CaseComment.case_id == case["id"], CaseComment.author == "svc_outsider")
            .count()
            == 0
        )
    finally:
        s.close()


def test_comment_history_is_participant_only():
    case = _make_case()
    client.post(
        f"/api/v1/core-hr/cases/{case['id']}/comments",
        json={"case_id": case["id"], "author": "svc_hr", "comment": "On it."},
        headers=HR_H,
    )
    for headers, expected in (
        (HR_H, 200),
        (ADMIN_H, 200),
        (OWNER_H, 200),
        (MGR_H, 200),
        (OUTSIDER_H, 404),
    ):
        r = client.get(f"/api/v1/core-hr/cases/{case['id']}/comments", headers=headers)
        assert r.status_code == expected, (headers, r.status_code, r.text)
    r = client.get(f"/api/v1/core-hr/cases/999999/comments", headers=OUTSIDER_H)
    assert r.status_code == 404, r.text


def test_case_list_filters_to_participants():
    case = _make_case(subject="Participant scoping probe")
    seen = {c["id"] for c in client.get("/api/v1/core-hr/cases", headers=HR_H).json()}
    assert case["id"] in seen, "HR sees every case"
    seen = {c["id"] for c in client.get("/api/v1/core-hr/cases", headers=ADMIN_H).json()}
    assert case["id"] in seen, "SuperAdmin sees every case"
    seen = {c["id"] for c in client.get("/api/v1/core-hr/cases", headers=OWNER_H).json()}
    assert case["id"] in seen, "the owner sees their own case"
    seen = {c["id"] for c in client.get("/api/v1/core-hr/cases", headers=MGR_H).json()}
    assert case["id"] in seen, "the assignee sees the assigned case"
    seen = {
        c["id"] for c in client.get("/api/v1/core-hr/cases", headers=OUTSIDER_H).json()
    }
    assert case["id"] not in seen, "an outsider must not see the case"


def test_non_admin_update_is_refused_and_missing_case_is_404():
    case = _make_case()
    r = client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"subject": "Hijack"}, headers=OWNER_H
    )
    assert r.status_code == 403, r.text
    r = client.put("/api/v1/core-hr/cases/999999", json={"subject": "x"}, headers=HR_H)
    assert r.status_code == 404, r.text


def test_comment_with_valid_attachment_is_stored():
    case = _make_case()
    r = client.post(
        f"/api/v1/core-hr/cases/{case['id']}/comments",
        json={
            "case_id": case["id"],
            "author": "svc_hr",
            "comment": "Payslip attached.",
            "attachment_filename": "payslip.pdf",
            "attachment_key": "/api/v1/files/cases/payslip.pdf",
        },
        headers=HR_H,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["attachment_filename"] == "payslip.pdf", body
    assert body["attachment_key"] == "/api/v1/files/cases/payslip.pdf", body


def test_comment_attachment_with_bad_prefix_is_refused():
    case = _make_case()
    r = client.post(
        f"/api/v1/core-hr/cases/{case['id']}/comments",
        json={
            "case_id": case["id"],
            "author": "svc_hr",
            "comment": "See this.",
            "attachment_filename": "evil.pdf",
            "attachment_key": "https://example.test/evil.pdf",
        },
        headers=HR_H,
    )
    assert r.status_code == 422, r.text


def test_comment_attachment_half_formed_is_refused():
    case = _make_case()
    r = client.post(
        f"/api/v1/core-hr/cases/{case['id']}/comments",
        json={
            "case_id": case["id"],
            "author": "svc_hr",
            "comment": "Key only.",
            "attachment_key": "/api/v1/files/cases/only.pdf",
        },
        headers=HR_H,
    )
    assert r.status_code == 422, r.text
    r = client.post(
        f"/api/v1/core-hr/cases/{case['id']}/comments",
        json={
            "case_id": case["id"],
            "author": "svc_hr",
            "comment": "Name only.",
            "attachment_filename": "only.pdf",
        },
        headers=HR_H,
    )
    assert r.status_code == 422, r.text
    s = SessionLocal()
    try:
        assert (
            s.query(CaseComment).filter(CaseComment.case_id == case["id"]).count() == 0
        )
    finally:
        s.close()


def test_comment_without_login_is_refused():
    case = _make_case()
    r = client.post(
        f"/api/v1/core-hr/cases/{case['id']}/comments",
        json={"case_id": case["id"], "author": "anon", "comment": "Hello?"},
    )
    assert r.status_code == 401, r.text


def test_every_mutation_is_audited():
    case = _make_case()
    client.put(
        f"/api/v1/core-hr/cases/{case['id']}", json={"status": "InProgress"}, headers=HR_H
    )
    r = client.post(
        f"/api/v1/core-hr/cases/{case['id']}/comments",
        json={"case_id": case["id"], "author": "svc_hr", "comment": "Noted."},
        headers=HR_H,
    )
    comment_id = r.json()["id"]
    s = SessionLocal()
    try:
        actions = {
            (row.action, row.entity_type, row.entity_id)
            for row in s.query(AuditLog)
            .filter(
                AuditLog.entity_type.in_(("HRCase", "CaseComment")),
                AuditLog.entity_id.in_((case["id"], comment_id)),
            )
            .all()
        }
    finally:
        s.close()
    assert ("create_hr_case", "HRCase", case["id"]) in actions, actions
    assert ("update_hr_case", "HRCase", case["id"]) in actions, actions
    assert ("add_case_comment", "CaseComment", comment_id) in actions, actions


def test_migration_0041_upgrades_a_fresh_database_to_head():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    try:
        env = dict(os.environ, DATABASE_URL=f"sqlite:///{tmp}")
        out = subprocess.run(
            [
                sys.executable,
                "-c",
                "from alembic.config import Config; "
                "from alembic import command; "
                "command.upgrade(Config('alembic.ini'), 'head')",
            ],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=env,
        )
        assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
        insp = inspect(create_engine(f"sqlite:///{tmp}"))
        cols = {c["name"] for c in insp.get_columns("case_comments")}
        assert {"attachment_filename", "attachment_key"} <= cols, cols
        from alembic.config import Config as _Config  # noqa: E402
        from alembic.script import ScriptDirectory as _Scripts  # noqa: E402

        scripts = _Scripts.from_config(
            _Config(os.path.join(os.path.dirname(os.path.abspath(__file__)), "alembic.ini"))
        )
        expected_heads = set(scripts.get_heads())
        engine = create_engine(f"sqlite:///{tmp}")
        try:
            with engine.connect() as conn:
                current = {
                    row[0]
                    for row in conn.exec_driver_sql(
                        "SELECT version_num FROM alembic_version"
                    )
                }
        finally:
            engine.dispose()
        assert current == expected_heads, (current, expected_heads)
    finally:
        os.unlink(tmp)


def main():
    for name, fn in [
        ("create defaults to Open with an audit row", test_create_defaults_to_open_with_audit),
        ("associate creates own case forced to self", test_associate_creates_own_case_forced_to_self),
        ("associate cannot create a case about a colleague", test_associate_cannot_create_case_about_colleague),
        ("associate without an employee link is refused", test_associate_without_employee_link_cannot_create_case),
        ("HR creates a case for any employee", test_hr_creates_case_for_any_employee),
        ("associate comments on own case", test_associate_comments_on_own_case),
        ("associate comment on another's case is 404", test_associate_comment_on_another_case_is_404),
        ("bad category is refused", test_bad_category_is_refused),
        ("bad priority is refused", test_bad_priority_is_refused),
        ("Open moves to InProgress", test_open_moves_to_in_progress),
        ("Open cannot skip to Resolved", test_open_cannot_skip_to_resolved),
        ("resolving requires a resolution", test_resolve_requires_a_resolution),
        ("resolving with a resolution stamps resolved_at", test_resolve_with_resolution_stamps_resolved_at),
        ("Resolved moves to Closed", test_resolved_moves_to_closed),
        ("Closed is terminal", test_closed_is_terminal),
        ("backward moves are refused", test_backward_move_is_refused),
        ("bad status literal is refused", test_bad_status_literal_is_refused),
        ("field edits without a status change are allowed", test_field_update_without_status_change_is_allowed),
        ("blank resolutions are refused", test_blank_resolution_is_refused),
        ("comments are append-only", test_comments_are_append_only),
        ("owner comments land, outsider comments are 404", test_owner_can_comment_but_outsider_gets_404),
        ("comment history is participant-only", test_comment_history_is_participant_only),
        ("case list filters to participants", test_case_list_filters_to_participants),
        ("non-admin updates refused, missing cases 404", test_non_admin_update_is_refused_and_missing_case_is_404),
        ("valid comment attachments are stored", test_comment_with_valid_attachment_is_stored),
        ("attachments off the files route are refused", test_comment_attachment_with_bad_prefix_is_refused),
        ("half-formed attachments are refused", test_comment_attachment_half_formed_is_refused),
        ("comments without a login are refused", test_comment_without_login_is_refused),
        ("every mutation is audited", test_every_mutation_is_audited),
        ("migration 0041 upgrades a fresh database to head", test_migration_0041_upgrades_a_fresh_database_to_head),
    ]:
        check(name, fn)
    print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
    for name, exc in _FAIL:
        print(f"FAIL  {name}: {exc!r}")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
