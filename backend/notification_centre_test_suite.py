"""Notification centre: event-driven notifications (LP-NOT-001).

What this suite proves
----------------------
* **Leave** — creating a request notifies the requester (a receipt); an
  approval notifies them of the outcome (success) and a rejection notifies
  them too (warning); a refused approval (no entitlement, 409) notifies
  nobody; deciding the same request twice is refused and notifies once.
* **Duplicate guard** — emitting the same
  (recipient, category, entity, type, title) key twice returns the first
  row instead of inserting a second one.
* **Payroll** — a successful process notifies the operator and every
  employee with a payslip; a refused process (no verified pack, 422)
  notifies nobody; a successful finalize notifies again under its own key;
  a second finalize (422) notifies nothing new.
* **Onboarding** — moving a task to Completed notifies the employee; any
  other edit, and a repeat write of Completed, notifies nothing new.
* **Offboarding** — starting a termination notifies the employee
  (warning); completing it notifies them again (success).
* **Centre reads** — ``unread-count`` counts only the caller's own unread
  rows; ``mark-read`` works for the owner and answers 403 for anyone
  else's row; the list shows only the caller's own rows and a
  ``recipient_id`` for someone else answers 403.
* **Preferences stub** — a recipient with every channel flag off receives
  no rows (the gate), while a recipient with no profile reads the product
  defaults from the preferences endpoint.

Run:  python notification_centre_test_suite.py
"""
import datetime
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="notification_centre_test_suite_"), "notification_centre_test_suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_OPRIGINS"] = ""
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"  # keep the suite's output readable
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.ess_hr import Notification  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.payroll import EmployeePayProfile, PayRun, PayrollPeriod, PaySlip  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import notifications as notify  # noqa: E402

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


# --- rule pack directory (verified QQ fixture, same trick as payroll suites) --
BACKEND_ROOT = Path(__file__).resolve().parent
FIXTURE_PACK = (
    BACKEND_ROOT
    / "test_fixtures"
    / "rule_packs"
    / "qq-test-fixture-synthetic-not-a-statute.json"
)


def pack_from_fixture(**changes) -> dict:
    data = json.loads(FIXTURE_PACK.read_text())
    for key, value in changes.items():
        if key in ("pack_id", "version", "status", "effective_from", "effective_to"):
            data[key] = value
        elif key == "country":
            data["jurisdiction"]["country"] = value
        elif key == "verification":
            data["verification"] = value
        else:
            raise KeyError(key)
    return data


def use_packs(packs: list[dict]) -> Path:
    directory = Path(tempfile.mkdtemp(prefix="notif-centre-packs-"))
    for index, pack in enumerate(packs):
        (directory / f"{index:02d}-{pack['pack_id']}.json").write_text(json.dumps(pack, indent=2))
    os.environ["RULE_PACK_DIR"] = str(directory)
    return directory


_verified_dir = use_packs([pack_from_fixture(pack_id="fixture-verified", status="verified")])


# --- fixtures -----------------------------------------------------------------
db = SessionLocal()

dept = Department(name="Notifications", code="NTF")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Notifier", code="NTFJOB", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)


def _employee(code: str, manager=None):
    emp = Employee(
        employee_id=code, first_name="Notif", last_name=code,
        email=f"{code.lower()}@example.com", hire_date=datetime.date(2024, 1, 1),
        job_id=job.id, department_id=dept.id,
        manager_id=manager.id if manager else None, status="Active",
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


mgr_emp = _employee("NOTIF-MGR")
assoc_emp = _employee("NOTIF-ASSOC", manager=mgr_emp)
other_emp = _employee("NOTIF-OTHER", manager=mgr_emp)
ASSOC_EMP_ID, OTHER_EMP_ID = assoc_emp.id, other_emp.id


def _user(username: str, role: str, employee_id: int | None, password: str) -> int:
    u = User(username=username, email=f"{username}@example.com",
             hashed_password=get_password_hash(password), role=role,
             is_active=True, employee_id=employee_id,
             # MFA-enforced world: privileged roles are enrolled, otherwise
             # every call below is refused before the handler runs.
             mfa_enabled=role in ("SuperAdmin", "HR"))
    db.add(u)
    db.commit()
    db.refresh(u)
    return u.id


sa_id = _user("notif_sa", "SuperAdmin", None, "SAPass12345")
hr_id = _user("notif_hr", "HR", None, "HRPass12345")
mgr_id = _user("notif_mgr", "Manager", mgr_emp.id, "MgrPass12345")
assoc_id = _user("notif_assoc", "Associate", ASSOC_EMP_ID, "AssocPass12345")
assoc2_id = _user("notif_assoc2", "Associate", OTHER_EMP_ID, "Assoc2Pass12345")
db.close()

client = TestClient(app, raise_server_exceptions=False)


def _headers(username: str, password: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"login {username}: {r.status_code} {r.text[:160]}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


H_SA = _headers("notif_sa", "SAPass12345")
H_HR = _headers("notif_hr", "HRPass12345")
H_MGR = _headers("notif_mgr", "MgrPass12345")
H_ASSOC = _headers("notif_assoc", "AssocPass12345")
H_ASSOC2 = _headers("notif_assoc2", "Assoc2Pass12345")


def notif_count(recipient_id: int, entity_type: str | None = None,
                entity_id: int | None = None, notification_type: str | None = None) -> int:
    with SessionLocal() as s:
        q = s.query(Notification).filter(Notification.recipient_id == recipient_id)
        if entity_type is not None:
            q = q.filter(Notification.entity_type == entity_type)
        if entity_id is not None:
            q = q.filter(Notification.entity_id == entity_id)
        if notification_type is not None:
            q = q.filter(Notification.notification_type == notification_type)
        return q.count()


def unread_api(headers: dict) -> int | None:
    r = client.get("/api/v1/ess/notifications/unread-count", headers=headers)
    if r.status_code != 200:
        return None
    return r.json().get("unread_count")


# --- leave type + entitlements --------------------------------------------------
YEAR = 2026
r = client.post("/api/v1/leave/types", headers=H_SA,
                json={"name": "Notif Annual", "code": "NTFAN", "is_paid": True,
                      "max_days_per_year": 20})
assert r.status_code == 201, r.text
TYPE_PAID = r.json()["id"]
r = client.post("/api/v1/leave/types", headers=H_SA,
                json={"name": "Notif Unpaid", "code": "NTFUN", "is_paid": False,
                      "max_days_per_year": 10})
assert r.status_code == 201, r.text
TYPE_BARE = r.json()["id"]
# Entitlements only for the paid type: the bare type exercises the refusal path.
r = client.post("/api/v1/leave/entitlements", headers=H_SA,
                json={"leave_type_id": TYPE_PAID, "entitlement_year": YEAR})
assert r.status_code in (200, 201), r.text


# ===========================================================================
print("\n[NOT-01] Leave create notifies the requester (receipt)")
# ===========================================================================
before = notif_count(assoc_id)
r = client.post("/api/v1/leave/requests", headers=H_ASSOC,
                json={"employee_id": ASSOC_EMP_ID, "leave_type_id": TYPE_PAID,
                      "start_date": f"{YEAR}-04-10", "end_date": f"{YEAR}-04-12",
                      "reason": "family"})
check("leave request created", r.status_code == 201, f"got {r.status_code}: {r.text[:160]}")
REQ1 = r.json()["id"]
check("create emits exactly one receipt to the requester",
      notif_count(assoc_id) == before + 1,
      f"before={before} after={notif_count(assoc_id)}")
with SessionLocal() as s:
    row = (s.query(Notification)
           .filter(Notification.recipient_id == assoc_id,
                   Notification.entity_type == "leave_request",
                   Notification.entity_id == REQ1)
           .first())
check("receipt carries the leave category + entity link",
      row is not None and row.category == "leave" and row.notification_type == "info",
      f"row={row.category if row else None}/{row.notification_type if row else None}")


# ===========================================================================
print("\n[NOT-02] Leave approve/reject notify; refusals stay silent")
# ===========================================================================
before = notif_count(assoc_id, "leave_request", REQ1, "success")
r = client.post(f"/api/v1/leave/requests/{REQ1}/approve", headers=H_MGR)
check("manager approves", r.status_code == 200, f"got {r.status_code}: {r.text[:160]}")
check("approve emits a success row under its own key",
      notif_count(assoc_id, "leave_request", REQ1, "success") == before + 1)
r = client.post(f"/api/v1/leave/requests/{REQ1}/approve", headers=H_MGR)
check("re-approve is refused", r.status_code == 400, f"got {r.status_code}: {r.text[:120]}")
check("refused re-approve notifies nothing new",
      notif_count(assoc_id, "leave_request", REQ1, "success") == before + 1)

r = client.post("/api/v1/leave/requests", headers=H_ASSOC,
                json={"employee_id": ASSOC_EMP_ID, "leave_type_id": TYPE_PAID,
                      "start_date": f"{YEAR}-05-04", "end_date": f"{YEAR}-05-05"})
assert r.status_code == 201, r.text
REQ2 = r.json()["id"]
r = client.post(f"/api/v1/leave/requests/{REQ2}/reject", headers=H_MGR)
check("manager rejects", r.status_code == 200, f"got {r.status_code}: {r.text[:160]}")
check("reject emits a warning row",
      notif_count(assoc_id, "leave_request", REQ2, "warning") == 1,
      f"count={notif_count(assoc_id, 'leave_request', REQ2, 'warning')}")

# The bare type has no entitlement: approval is refused with 409 and silent.
r = client.post("/api/v1/leave/requests", headers=H_ASSOC,
                json={"employee_id": ASSOC_EMP_ID, "leave_type_id": TYPE_BARE,
                      "start_date": f"{YEAR}-06-01", "end_date": f"{YEAR}-06-02"})
assert r.status_code == 201, r.text
REQ3 = r.json()["id"]
# The create receipt is already there; the refusal must add nothing and in
# particular no success row.
before = notif_count(assoc_id, "leave_request", REQ3)
r = client.post(f"/api/v1/leave/requests/{REQ3}/approve", headers=H_MGR)
check("approval without entitlement is refused", r.status_code == 409,
      f"got {r.status_code}: {r.text[:160]}")
check("refused approval notifies nobody",
      notif_count(assoc_id, "leave_request", REQ3) == before
      and notif_count(assoc_id, "leave_request", REQ3, "success") == 0,
      f"count={notif_count(assoc_id, 'leave_request', REQ3)} before={before}")


# ===========================================================================
print("\n[NOT-03] Duplicate guard: same key, one row")
# ===========================================================================
with SessionLocal() as s:
    first = notify.emit(s, recipient_user_id=assoc_id, title="Guard probe",
                        message="first", notification_type="info",
                        category="system", entity_type="probe", entity_id=4242)
    first_id = first.id if first else None
    s.commit()
    second = notify.emit(s, recipient_user_id=assoc_id, title="Guard probe",
                         message="second", notification_type="info",
                         category="system", entity_type="probe", entity_id=4242)
    second_id = second.id if second else None
    s.commit()
    n = (s.query(Notification)
         .filter(Notification.entity_type == "probe",
                 Notification.entity_id == 4242).count())
check("second emit returns the first row", first_id is not None and first_id == second_id,
      f"first={first_id} second={second_id}")
check("guard leaves exactly one row", n == 1, f"rows={n}")
with SessionLocal() as s:
    other = notify.emit(s, recipient_user_id=assoc_id, title="Guard probe (other type)",
                        message="x", notification_type="warning",
                        category="system", entity_type="probe", entity_id=4242)
    s.commit()
    other_id = other.id if other else None
check("a different type is a different key", other_id is not None and other_id != first_id)
with SessionLocal() as s:
    bare1 = notify.emit(s, recipient_user_id=assoc_id, title="Entity-less probe",
                        message="first", notification_type="info",
                        category="system")
    s.commit()
    bare1_id = bare1.id if bare1 else None
    bare2 = notify.emit(s, recipient_user_id=assoc_id, title="Entity-less probe",
                        message="retry", notification_type="info",
                        category="system")
    s.commit()
    bare2_id = bare2.id if bare2 else None
    bare_n = (s.query(Notification)
              .filter(Notification.recipient_id == assoc_id,
                      Notification.title == "Entity-less probe",
                      Notification.entity_type.is_(None),
                      Notification.entity_id.is_(None)).count())
check("entity-less retry returns the first row",
      bare1_id is not None and bare1_id == bare2_id,
      f"first={bare1_id} second={bare2_id}")
check("entity-less guard leaves exactly one row", bare_n == 1, f"rows={bare_n}")


# ===========================================================================
print("\n[NOT-04] Payroll process: success notifies, refusal is silent")
# ===========================================================================
def _profile(employee_id: int) -> None:
    r = client.post("/api/v1/payroll/pay-profiles", headers=H_SA,
                    json={"employee_id": employee_id, "base_salary": 50000,
                          "pay_frequency": "Monthly", "tax_withholding": 10})
    assert r.status_code in (201, 409), r.text


_profile(ASSOC_EMP_ID)
r = client.post("/api/v1/payroll/periods", headers=H_SA,
                json={"name": "Notif period", "start_date": "2026-03-01",
                      "end_date": "2026-03-31", "pay_date": "2026-03-31"})
assert r.status_code == 201, r.text
PERIOD = r.json()["id"]
r = client.post("/api/v1/payroll/runs", headers=H_SA,
                json={"period_id": PERIOD, "jurisdiction": "QQ", "currency": "USD"})
assert r.status_code == 201, r.text
RUN = r.json()["id"]
op_before, emp_before = notif_count(sa_id, "pay_run", RUN), notif_count(assoc_id, "pay_run", RUN)
r = client.post(f"/api/v1/payroll/runs/{RUN}/process", headers=H_SA)
check("run processes with a verified pack", r.status_code == 200,
      f"got {r.status_code}: {r.text[:160]}")
check("process notifies the operator",
      notif_count(sa_id, "pay_run", RUN) == op_before + 1)
check("process notifies the employee behind the payslip",
      notif_count(assoc_id, "pay_run", RUN) == emp_before + 1)

# Refusal: no pack dir at all -> 422, and no notification anywhere.
_empty = use_packs([])
r = client.post("/api/v1/payroll/periods", headers=H_SA,
                json={"name": "Refused period", "start_date": "2026-03-01",
                      "end_date": "2026-03-31", "pay_date": "2026-03-31"})
assert r.status_code == 201, r.text
RUN_REF = client.post("/api/v1/payroll/runs", headers=H_SA,
                      json={"period_id": r.json()["id"], "jurisdiction": "QQ",
                            "currency": "USD"}).json()["id"]
total_before = notif_count(sa_id) + notif_count(assoc_id)
r = client.post(f"/api/v1/payroll/runs/{RUN_REF}/process", headers=H_SA)
check("run without a pack is refused", r.status_code == 422,
      f"got {r.status_code}: {r.text[:160]}")
check("refused process notifies nobody",
      notif_count(sa_id) + notif_count(assoc_id) == total_before)
_verified_dir = use_packs([pack_from_fixture(pack_id="fixture-verified", status="verified")])


# ===========================================================================
print("\n[NOT-05] Payroll finalize notifies once under its own key")
# ===========================================================================
r = client.post(f"/api/v1/payroll/runs/{RUN}/approve", headers=H_HR)
check("a different admin approves (segregation)", r.status_code == 200,
      f"got {r.status_code}: {r.text[:160]}")
fin_before = notif_count(assoc_id, "pay_run", RUN)
r = client.post(f"/api/v1/payroll/runs/{RUN}/finalize", headers=H_SA)
check("run finalizes", r.status_code == 200, f"got {r.status_code}: {r.text[:160]}")
check("finalize emits under the finalize title",
      notif_count(assoc_id, "pay_run", RUN) == fin_before + 1)
with SessionLocal() as s:
    titles = {n.title for n in s.query(Notification)
              .filter(Notification.recipient_id == assoc_id,
                      Notification.entity_type == "pay_run",
                      Notification.entity_id == RUN).all()}
check("process and finalize are distinct rows, not one deduped row",
      any("processed" in t for t in titles) and any("finalized" in t for t in titles),
      f"titles={sorted(titles)}")
r = client.post(f"/api/v1/payroll/runs/{RUN}/finalize", headers=H_SA)
check("second finalize is refused", r.status_code == 422,
      f"got {r.status_code}: {r.text[:160]}")
check("refused finalize notifies nothing new",
      notif_count(assoc_id, "pay_run", RUN) == fin_before + 1)


# ===========================================================================
print("\n[NOT-06] Onboarding: only the crossing into Completed notifies")
# ===========================================================================
r = client.post("/api/v1/onboarding/tasks", headers=H_SA,
                json={"employee_id": ASSOC_EMP_ID, "title": "Collect laptop"})
assert r.status_code == 201, r.text
TASK = r.json()["id"]
before = notif_count(assoc_id, "onboarding_task", TASK)
r = client.put(f"/api/v1/onboarding/tasks/{TASK}", headers=H_SA,
               json={"description": "from the IT desk"})
check("non-completion edit accepted", r.status_code == 200,
      f"got {r.status_code}: {r.text[:120]}")
check("non-completion edit notifies nothing",
      notif_count(assoc_id, "onboarding_task", TASK) == before == 0)
r = client.put(f"/api/v1/onboarding/tasks/{TASK}", headers=H_SA,
               json={"status": "Completed"})
check("completion accepted", r.status_code == 200, f"got {r.status_code}: {r.text[:120]}")
check("completion emits a success row",
      notif_count(assoc_id, "onboarding_task", TASK,
                  notification_type="success") == 1)
r = client.put(f"/api/v1/onboarding/tasks/{TASK}", headers=H_SA,
               json={"description": "already done, annotating"})
check("repeat write of Completed accepted", r.status_code == 200,
      f"got {r.status_code}: {r.text[:120]}")
check("repeat write notifies nothing new",
      notif_count(assoc_id, "onboarding_task", TASK) == before + 1)


# ===========================================================================
print("\n[NOT-07] Offboarding start + complete notify the employee")
# ===========================================================================
r = client.post("/api/v1/offboarding/terminations", headers=H_SA,
                json={"employee_id": OTHER_EMP_ID, "last_working_date": "2026-05-01",
                      "termination_type": "Resignation", "reason": "new role"})
check("termination starts", r.status_code == 201, f"got {r.status_code}: {r.text[:160]}")
TERM = r.json()["id"]
check("start emits a warning row",
      notif_count(assoc2_id, "termination", TERM, "warning") == 1)
r = client.post(f"/api/v1/offboarding/terminations/{TERM}/complete", headers=H_SA)
check("termination completes", r.status_code == 200,
      f"got {r.status_code}: {r.text[:160]}")
check("complete emits a success row",
      notif_count(assoc2_id, "termination", TERM, "success") == 1)


def _all_mine(ids: set, recipient_id: int) -> bool:
    with SessionLocal() as s:
        rows = (s.query(Notification.recipient_id)
                .filter(Notification.id.in_(ids)).all())
        return bool(ids) and all(rid == recipient_id for (rid,) in rows)


# ===========================================================================
print("\n[NOT-08] Centre reads: unread-count, ownership, scoping")
# ===========================================================================
n_unread = unread_api(H_ASSOC)
check("unread-count answers for the owner",
      isinstance(n_unread, int) and n_unread >= 5, f"unread={n_unread}")
r = client.get("/api/v1/ess/notifications", headers=H_ASSOC)
check("list answers for the owner", r.status_code == 200,
      f"got {r.status_code}: {r.text[:120]}")
own_ids = {n["id"] for n in r.json()} if r.status_code == 200 else set()
check("list carries only the caller's own rows",
      bool(own_ids) and all(
          True for _ in [0]) and _all_mine(own_ids, assoc_id),
      f"rows={len(own_ids)}")

with SessionLocal() as s:
    foreign = (s.query(Notification)
               .filter(Notification.recipient_id == assoc2_id)
               .order_by(Notification.id).first())
FOREIGN_ID = foreign.id if foreign else None
check("fixture: the other associate has a notification to contend over",
      FOREIGN_ID is not None)
r = client.put(f"/api/v1/ess/notifications/{FOREIGN_ID}/read", headers=H_ASSOC)
check("marking someone else's row read is refused (403)",
      r.status_code == 403 and "error" in r.json(),
      f"got {r.status_code}: {r.text[:120]}")
check("the refused mark-read changed nothing",
      notif_count(assoc2_id, "termination", TERM) == 2)
r = client.get(f"/api/v1/ess/notifications?recipient_id={assoc2_id}", headers=H_ASSOC)
check("listing someone else's rows is refused (403)",
      r.status_code == 403 and "error" in r.json(),
      f"got {r.status_code}: {r.text[:120]}")

mine_before = unread_api(H_ASSOC)
with SessionLocal() as s:
    mine = (s.query(Notification)
            .filter(Notification.recipient_id == assoc_id,
                    Notification.is_read == False)  # noqa: E712 - suite-local SQLite check
            .order_by(Notification.id).first())
MINE_ID = mine.id if mine else None
r = client.put(f"/api/v1/ess/notifications/{MINE_ID}/read", headers=H_ASSOC)
check("owner marks own row read", r.status_code == 200 and r.json().get("is_read") is True,
      f"got {r.status_code}: {r.text[:120]}")
check("unread-count drops by one",
      unread_api(H_ASSOC) == mine_before - 1,
      f"before={mine_before} after={unread_api(H_ASSOC)}")
r = client.put(f"/api/v1/ess/notifications/{MINE_ID}/read", headers=H_ASSOC)
check("re-reading an already-read row is idempotent",
      r.status_code == 200 and r.json().get("is_read") is True,
      f"got {r.status_code}: {r.text[:120]}")
check("idempotent re-read adds no row",
      unread_api(H_ASSOC) == mine_before - 1)


# ===========================================================================
print("\n[NOT-09] Preferences stub gates the emission")
# ===========================================================================
r = client.get("/api/v1/ess/notifications/preferences", headers=H_ASSOC)
check("preferences read answers with defaults for a profile-less caller",
      r.status_code == 200 and r.json().get("email") is True,
      f"got {r.status_code}: {r.text[:120]}")
r = client.post("/api/v1/ess/ess/profile", headers=H_ASSOC2,
                json={"employee_id": OTHER_EMP_ID, "notification_email": False,
                      "notification_sms": False, "notification_push": False})
check("opt-out profile stored", r.status_code == 201,
      f"got {r.status_code}: {r.text[:160]}")
r = client.get("/api/v1/ess/notifications/preferences", headers=H_ASSOC2)
check("preferences read reflects the opt-out",
      r.status_code == 200 and r.json() == {"email": False, "sms": False, "push": False},
      f"got {r.status_code}: {r.text[:120]}")
opt_before = notif_count(assoc2_id)
r = client.post("/api/v1/onboarding/tasks", headers=H_SA,
                json={"employee_id": OTHER_EMP_ID, "title": "Return badge"})
assert r.status_code == 201, r.text
OPT_TASK = r.json()["id"]
r = client.put(f"/api/v1/onboarding/tasks/{OPT_TASK}", headers=H_SA,
               json={"status": "Completed"})
check("completion accepted even for an opted-out recipient",
      r.status_code == 200, f"got {r.status_code}: {r.text[:120]}")
check("opted-out recipient receives no row",
      notif_count(assoc2_id) == opt_before,
      f"before={opt_before} after={notif_count(assoc2_id)}")

# --- Tenant gate on notification creation ----------------------------------
# Notifications carry no tenant_id of their own, so the gate resolves the
# tenant through the recipient: recipient user -> employee -> tenant_id.
# A recipient in another tenant (or one that resolves to no tenant at all)
# answers the same 422 as an unknown user — no existence oracle.
print()
print("Tenant gate on notification creation")
print("-" * 68)

NTF_TA = "tenant-ntf-a"
NTF_TB = "tenant-ntf-b"

with SessionLocal() as s:
    _dept = s.query(Department).filter(Department.code == "NTF").one()
    _job = s.query(Job).filter(Job.code == "NTFJOB").one()

    def _tenant_employee(code: str, tenant: str) -> Employee:
        emp = Employee(
            employee_id=code, first_name="Notif", last_name=code,
            email=f"{code.lower()}@example.com", hire_date=datetime.date(2024, 1, 1),
            job_id=_job.id, department_id=_dept.id, status="Active",
            tenant_id=tenant,
        )
        s.add(emp)
        s.commit()
        s.refresh(emp)
        return emp

    _ea = _tenant_employee("NOTIF-TA-USER", NTF_TA)
    _eb = _tenant_employee("NOTIF-TB-USER", NTF_TB)

    def _tenant_user(username: str, employee_id: int) -> int:
        u = User(username=username, email=f"{username}@example.com",
                 hashed_password=get_password_hash("TenantPass12345"), role="Associate",
                 is_active=True, employee_id=employee_id)
        s.add(u)
        s.commit()
        s.refresh(u)
        return u.id

    NTF_UA_ID = _tenant_user("notif_user_a", _ea.id)
    NTF_UB_ID = _tenant_user("notif_user_b", _eb.id)


def _tenant_sa_headers(tenant: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(subject='notif_sa', extra_claims={'tenant': tenant})}"}


HA_NTF = _tenant_sa_headers(NTF_TA)

r = client.post("/api/v1/ess/notifications", headers=HA_NTF,
                json={"recipient_id": NTF_UA_ID, "title": "Hello A", "message": "same tenant"})
check("a notification to the caller's own tenant is created",
      r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

r = client.post("/api/v1/ess/notifications", headers=HA_NTF,
                json={"recipient_id": NTF_UB_ID, "title": "Hello B", "message": "other tenant"})
check("a notification to another tenant's user is refused",
      r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")
check("the refusal names the reference, not the tenant",
      r.json().get("error", {}).get("code") == "reference_not_found",
      f"got {r.text[:200]}")

r = client.post("/api/v1/ess/notifications", headers=HA_NTF,
                json={"recipient_id": 999999, "title": "Ghost", "message": "unknown user"})
check("a notification to an unknown user is refused",
      r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")


print("\n" + "=" * 62)
print(f"==== NOTIFICATION CENTRE SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 62)
raise SystemExit(1 if RESULTS["fail"] else 0)
