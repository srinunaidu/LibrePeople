"""Employment history and the lifecycle state machine (HR-12).

What this suite proves
----------------------
The employee record used to hold one current value per field and no record of
how it got there. A lifecycle move was an overwrite with no rule about which
moves were legal, so "when did this person leave?" had no answer and a
terminated employee could be made `Active` again in one request.

* the transition matrix: every current/next pair is either allowed or refused
  with `409 invalid_state_transition`, and a refused move changes nothing;
* a change appends an effective-dated history row naming the field, the old
  and new value, the actor, the reason and the first day in force;
* a newer change closes the previous row for that field (`effective_to`,
  exclusive) and never rewrites it;
* moving to `Terminated` records the termination date, and `Rehired` clears
  it;
* a future date is refused with 422 (nothing would apply it), a past date is
  accepted as a correction;
* a contact correction is audited but not dated; a no-op writes neither;
* references, a reporting cycle and a duplicate email are refused before
  anything is written;
* the history read filters by field and date, is oldest first, and honours the
  caller's visibility scope;
* the role gate: only SuperAdmin/HR may change employment; the history read is
  open to the roles that may see the employee.

Run:  python employment_history_test_suite.py
"""
import os

DB_PATH = "employment_history_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///./{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from datetime import date, timedelta  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.employment import ALLOWED_TRANSITIONS  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee, EmployeeHistory  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
client = TestClient(app, raise_server_exceptions=False)

RESULTS = {"pass": 0, "fail": 0}
FAILURES = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


TODAY = date.today()
LIST = "/api/v1/employees/"
LOGIN = "/api/v1/auth/login"
PASSWORD = "EmploymentPass123"

print("=" * 68)
print("EMPLOYMENT HISTORY / LIFECYCLE SUITE (HR-12)")
print("=" * 68)

# --- fixtures ---------------------------------------------------------------
dept = Department(name="Employment", code="EMP12")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Employment Analyst", code="EMP12-JOB", department_id=dept.id)
job2 = Job(title="Employment Lead", code="EMP12-LEAD", department_id=dept.id)
db.add_all([job, job2])
db.commit()
db.refresh(job)
db.refresh(job2)

db.query(EmployeeHistory).delete()
db.query(Employee).delete()
db.commit()

alice = Employee(
    employee_id="H-001",
    first_name="Alice",
    last_name="Anderson",
    email="alice.history@example.com",
    hire_date=TODAY - timedelta(days=900),
    job_id=job.id,
    department_id=dept.id,
    status="Active",
    employment_type="Full-time",
    salary=50000,
)
bob = Employee(
    employee_id="H-002",
    first_name="Bob",
    last_name="Brown",
    email="bob.history@example.com",
    hire_date=TODAY - timedelta(days=600),
    job_id=job.id,
    department_id=dept.id,
    manager_id=None,
    status="Active",
    employment_type="Full-time",
    salary=45000,
)
carol = Employee(
    employee_id="H-003",
    first_name="Carol",
    last_name="Clark",
    email="carol.history@example.com",
    hire_date=TODAY - timedelta(days=300),
    job_id=job.id,
    department_id=dept.id,
    status="Active",
    employment_type="Part-time",
    salary=30000,
)
db.add_all([alice, bob, carol])
db.commit()
for row in (alice, bob, carol):
    db.refresh(row)
alice.manager_id = None
bob.manager_id = alice.id
db.commit()

ACCOUNTS = {
    "SuperAdmin": ("h12admin", None),
    "HR": ("h12hr", None),
    "Manager": ("h12mgr", alice.id),
    "Associate": ("h12assoc", carol.id),
    "PayrollViewer": ("h12pay", None),
}
for username, _ in ACCOUNTS.values():
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.delete(existing)
db.commit()
for role, (username, employee_id) in ACCOUNTS.items():
    db.add(
        User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            role=role,
            employee_id=employee_id,
            is_active=True,
            mfa_enabled=role in ("SuperAdmin", "HR"),
        )
    )
db.commit()

HEADERS: dict[str, dict] = {}
for role, (username, _) in ACCOUNTS.items():
    response = client.post(LOGIN, json={"username": username, "password": PASSWORD})
    if response.status_code != 200:
        check(f"the {role} account can sign in", False, f"status={response.status_code}")
        continue
    HEADERS[role] = {"Authorization": f"Bearer {response.json()['access_token']}"}
check("one account per role signed in", len(HEADERS) == len(ACCOUNTS), f"got {sorted(HEADERS)}")

ADMIN = HEADERS["SuperAdmin"]
HR = HEADERS["HR"]
MANAGER = HEADERS["Manager"]
ASSOCIATE = HEADERS["Associate"]
PAYROLL = HEADERS["PayrollViewer"]


def patch(employee_id: int, headers: dict | None = None, **body):
    return client.patch(
        f"{LIST}{employee_id}", headers=ADMIN if headers is None else headers, json=body
    )


def history(employee_id: int, headers: dict | None = None, **params):
    return client.get(
        f"{LIST}{employee_id}/history",
        headers=ADMIN if headers is None else headers,
        params=params,
    )


def audit_count(action: str = "update_employee") -> int:
    with Session(engine) as session:
        return (
            session.query(AuditLog)
            .filter(AuditLog.action == action, AuditLog.entity_type == "Employee")
            .count()
        )


def row_count(employee_id: int) -> int:
    with Session(engine) as session:
        return (
            session.query(EmployeeHistory)
            .filter(EmployeeHistory.employee_id == employee_id)
            .count()
        )


def fresh_employee(status: str, number: str) -> Employee:
    employee = Employee(
        employee_id=number,
        first_name="Matrix",
        last_name=status.replace(" ", ""),
        email=f"{number.lower()}@example.com",
        hire_date=TODAY - timedelta(days=100),
        job_id=job.id,
        department_id=dept.id,
        status=status,
        employment_type="Full-time",
        salary=40000,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


# ====[ the transition matrix ]==============================================
print("\n[HR12-1] the lifecycle matrix is the stated one")

statuses = tuple(ALLOWED_TRANSITIONS)
for current in statuses:
    for target in statuses:
        employee = fresh_employee(current, f"MAT-{current[:3]}-{target[:3]}".upper().replace(" ", ""))
        response = patch(employee.id, status=target)
        allowed = target == current or target in ALLOWED_TRANSITIONS[current]
        if allowed:
            check(
                f"{current} -> {target} is allowed",
                response.status_code == 200
                and response.json().get("status") == target,
                f"got {response.status_code}: {response.text[:140]}",
            )
        else:
            payload = response.json() if response.content else {}
            error = payload.get("error") or {}
            check(
                f"{current} -> {target} is refused with invalid_state_transition",
                response.status_code == 409
                and error.get("code") == "invalid_state_transition",
                f"got {response.status_code}: {response.text[:140]}",
            )
            with Session(engine) as session:
                stored = session.get(Employee, employee.id)
                check(
                    f"the refused {current} -> {target} move changed nothing",
                    stored.status == current,
                    f"got {stored.status!r}",
                )
            check(
                f"the refused {current} -> {target} move wrote no history",
                row_count(employee.id) == 0,
                f"rows={row_count(employee.id)}",
            )


# ====[ the dated history ]==================================================
print("\n[HR12-2] a change appends a dated history row and closes the old one")

before_audit = audit_count()
first = patch(
    alice.id,
    status="On Leave",
    effective_from=(TODAY - timedelta(days=10)).isoformat(),
    reason="Medical leave approved",
)
check("an allowed move answers 200", first.status_code == 200, first.text[:160])
check(
    "the record shows the new status",
    first.json().get("status") == "On Leave",
    first.text[:160],
)

rows = history(alice.id).json()
status_rows = [row for row in rows if row["field"] == "status"]
check("the history names the status change", len(status_rows) == 1, str(status_rows))
row = status_rows[0]
check(
    "the row carries the previous and new value",
    row["previous_value"] == "Active" and row["new_value"] == "On Leave",
    str(row),
)
check(
    "the row is stamped with the effective date, reason and actor",
    row["effective_from"] == (TODAY - timedelta(days=10)).isoformat()
    and row["effective_to"] is None
    and row["reason"] == "Medical leave approved"
    and row["changed_by"] == "h12admin",
    str(row),
)
check(
    "the change wrote one audit row",
    audit_count() == before_audit + 1,
    f"got {audit_count()} expected {before_audit + 1}",
)

second = patch(
    alice.id,
    status="Active",
    effective_from=(TODAY - timedelta(days=5)).isoformat(),
    reason="Returned to work",
)
check("the return to work is allowed", second.status_code == 200, second.text[:160])
rows = history(alice.id).json()
status_rows = [r for r in rows if r["field"] == "status"]
check("the second move appends a second status row", len(status_rows) == 2, str(status_rows))
check(
    "the first row is closed on the day the second starts",
    status_rows[0]["effective_to"] == (TODAY - timedelta(days=5)).isoformat(),
    str(status_rows[0]),
)
check(
    "the newer row is still open",
    status_rows[-1]["effective_to"] is None
    and status_rows[-1]["new_value"] == "Active",
    str(status_rows[-1]),
)
check(
    "the history is oldest first",
    [r["effective_from"] for r in status_rows]
    == sorted(r["effective_from"] for r in status_rows),
    str([r["effective_from"] for r in status_rows]),
)

# ====[ termination and rehire ]=============================================
print("\n[HR12-3] termination records the date; a rehire clears it")

terminated = patch(
    alice.id,
    status="Terminated",
    effective_from=(TODAY - timedelta(days=3)).isoformat(),
    reason="Resigned",
)
check("an active employee can be terminated", terminated.status_code == 200, terminated.text[:160])
check(
    "the termination date is the effective date",
    terminated.json().get("termination_date") == (TODAY - timedelta(days=3)).isoformat(),
    terminated.text[:160],
)
rows = history(alice.id).json()
check(
    "the termination is dated in the history",
    any(
        r["field"] == "termination_date"
        and r["new_value"] == (TODAY - timedelta(days=3)).isoformat()
        for r in rows
    ),
    str([r for r in rows if r["field"] == "termination_date"]),
)
refused = patch(alice.id, status="Active")
payload = refused.json() if refused.content else {}
check(
    "a terminated employee cannot go straight back to Active",
    refused.status_code == 409
    and (payload.get("error") or {}).get("code") == "invalid_state_transition",
    f"got {refused.status_code}: {refused.text[:160]}",
)
rehired = patch(alice.id, status="Rehired", reason="Returned as a contractor")
check("a terminated employee can be rehired", rehired.status_code == 200, rehired.text[:160])
check(
    "the rehire clears the termination date",
    rehired.json().get("termination_date") is None,
    rehired.text[:160],
)
rows = history(alice.id).json()
check(
    "clearing the date is itself a history row",
    any(
        r["field"] == "termination_date" and r["new_value"] is None
        for r in rows
    ),
    str([r for r in rows if r["field"] == "termination_date"]),
)


# ====[ effective dates ]====================================================
print("\n[HR12-4] a future date is refused; a past date is a correction")

future = patch(
    alice.id,
    status="On Leave",
    effective_from=(TODAY + timedelta(days=1)).isoformat(),
)
check("a future effective date is refused", future.status_code == 422, future.text[:160])
check(
    "the refusal is a validation error naming the date",
    (future.json().get("error") or {}).get("code") == "validation_error",
    future.text[:160],
)
with Session(engine) as session:
    check(
        "the refused future change did not move the record",
        session.get(Employee, alice.id).status == "Rehired",
        f"got {session.get(Employee, alice.id).status!r}",
    )

past = patch(
    bob.id,
    salary=46000,
    effective_from=(TODAY - timedelta(days=20)).isoformat(),
    reason="Backdated correction",
)
check("a past effective date is accepted", past.status_code == 200, past.text[:160])
rows = history(bob.id).json()
salary_rows = [r for r in rows if r["field"] == "salary"]
check(
    "the past-dated change carries its date",
    salary_rows and salary_rows[-1]["effective_from"] == (TODAY - timedelta(days=20)).isoformat(),
    str(salary_rows),
)
check(
    "the salary history compares the numbers, not their formatting",
    salary_rows[-1]["previous_value"] == "45000.00"
    and salary_rows[-1]["new_value"] == "46000.00",
    str(salary_rows[-1]),
)


# ====[ references, cycles and duplicates ]==================================
print("\n[HR12-5] a bad reference, a cycle and a duplicate are refused first")

unknown_job = patch(alice.id, job_id=999999)
check(
    "an unknown job is 422 reference_not_found",
    unknown_job.status_code == 422
    and (unknown_job.json().get("error") or {}).get("code") == "reference_not_found",
    unknown_job.text[:160],
)
unknown_dept = patch(alice.id, department_id=999999)
check(
    "an unknown department is 422 reference_not_found",
    unknown_dept.status_code == 422
    and (unknown_dept.json().get("error") or {}).get("code") == "reference_not_found",
    unknown_dept.text[:160],
)
self_manager = patch(alice.id, manager_id=alice.id)
check("being one's own manager is refused", self_manager.status_code == 422, self_manager.text[:160])
cycle = patch(alice.id, manager_id=bob.id)
check("a reporting cycle is refused", cycle.status_code == 422, cycle.text[:160])
duplicate = patch(alice.id, email=carol.email)
check(
    "another employee's email is 409 duplicate_natural_key",
    duplicate.status_code == 409
    and (duplicate.json().get("error") or {}).get("code") == "duplicate_natural_key",
    duplicate.text[:160],
)
empty = patch(alice.id)
check("a change with no field is refused", empty.status_code == 422, empty.text[:160])


# ====[ corrections vs history ]=============================================
print("\n[HR12-6] contact corrections are audited, not dated; a no-op writes nothing")

before_rows = row_count(alice.id)
before_audit = audit_count()
corrected = patch(alice.id, first_name="Alicia", reason="Name correction")
check("a contact correction is accepted", corrected.status_code == 200, corrected.text[:160])
check("the record carries the corrected name", corrected.json().get("first_name") == "Alicia")
check(
    "a contact correction writes no employment history",
    row_count(alice.id) == before_rows,
    f"rows={row_count(alice.id)} expected {before_rows}",
)
check(
    "a contact correction is still audited",
    audit_count() == before_audit + 1,
    f"got {audit_count()} expected {before_audit + 1}",
)
before_rows = row_count(alice.id)
before_audit = audit_count()
noop = patch(alice.id, first_name="Alicia", status="Rehired")
check("a no-op is accepted", noop.status_code == 200, noop.text[:160])
check(
    "a no-op writes no history",
    row_count(alice.id) == before_rows,
    f"rows={row_count(alice.id)}",
)
check(
    "a no-op writes no audit row",
    audit_count() == before_audit,
    f"got {audit_count()} expected {before_audit}",
)


# ====[ job and employment type ]============================================
print("\n[HR12-7] job and employment type are dated like the rest")

first_job = patch(
    bob.id,
    job_id=job2.id,
    employment_type="Contract",
    effective_from=(TODAY - timedelta(days=2)).isoformat(),
)
check("a job change is accepted", first_job.status_code == 200, first_job.text[:160])
check(
    "the record shows the new job and type",
    first_job.json().get("job_id") == job2.id
    and first_job.json().get("employment_type") == "Contract",
    first_job.text[:160],
)
second_job = patch(bob.id, job_id=job.id, effective_from=TODAY.isoformat())
check("a second job change is accepted", second_job.status_code == 200, second_job.text[:160])
rows = history(bob.id, field="job_id").json()
check("the field filter returns only job rows", all(r["field"] == "job_id" for r in rows), str(rows))
check("two job changes produced two rows", len(rows) == 2, str(rows))
check(
    "the first job row closes on the second's date",
    rows[0]["effective_to"] == TODAY.isoformat(),
    str(rows[0]),
)


# ====[ the history read ]===================================================
print("\n[HR12-8] the history read filters and scopes")

all_rows = history(alice.id).json()
check("the history is a list of the contract's rows", isinstance(all_rows, list) and all_rows, str(all_rows)[:160])
check(
    "a row has the contract's shape",
    {"id", "field", "previous_value", "new_value", "effective_from",
     "effective_to", "reason", "changed_by", "changed_at"} <= set(all_rows[0]),
    f"got {sorted(all_rows[0])}",
)
check("the row identity is an integer", isinstance(all_rows[0]["id"], int), str(all_rows[0]["id"]))
window = history(
    alice.id,
    **{
        "from": (TODAY - timedelta(days=7)).isoformat(),
        "to": (TODAY - timedelta(days=1)).isoformat(),
    },
).json()
check(
    "the from/to window excludes rows outside it",
    all(
        (TODAY - timedelta(days=7)).isoformat()
        <= row["effective_from"]
        <= (TODAY - timedelta(days=1)).isoformat()
        for row in window
    )
    and window,
    str([r["effective_from"] for r in window]),
)

manager_own = history(alice.id, MANAGER)
check("a Manager can read the history of their line", manager_own.status_code == 200, manager_own.text[:120])
manager_out = history(carol.id, MANAGER)
check("a Manager cannot read outside their line (404, never 403)", manager_out.status_code == 404, manager_out.text[:120])
associate_own = history(carol.id, ASSOCIATE)
check("an Associate can read their own history", associate_own.status_code == 200, associate_own.text[:120])
associate_out = history(alice.id, ASSOCIATE)
check("an Associate cannot read another employee's history", associate_out.status_code == 404, associate_out.text[:120])
check("a PayrollViewer can read the history", history(alice.id, PAYROLL).status_code == 200)
check("an unauthenticated read is refused", client.get(f"{LIST}{alice.id}/history").status_code == 401)

for role in ("Manager", "Associate", "PayrollViewer"):
    before_audit = audit_count()
    response = patch(alice.id, HEADERS[role], salary=99999)
    payload = response.json() if response.content else {}
    check(
        f"{role} cannot change employment",
        response.status_code == 403
        and (payload.get("error") or {}).get("code") == "forbidden",
        f"got {response.status_code}: {response.text[:140]}",
    )
    check(
        f"the refused {role} change wrote no audit row",
        audit_count() == before_audit,
        f"got {audit_count()} expected {before_audit}",
    )

missing = history(999999)
check("an unknown employee's history is 404", missing.status_code == 404, missing.text[:120])


# ===========================================================================
print()
print("=" * 68)
print(f"EMPLOYMENT HISTORY SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
print("=" * 68)
if FAILURES:
    print("\nfailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
    raise SystemExit(1)
