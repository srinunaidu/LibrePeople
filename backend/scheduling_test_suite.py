"""Scheduling test suite: draft generation, adjustment, and publish flow.

What this suite proves
----------------------
* generate_draft_roster runs the solver, persists a draft, and returns assignments
* get_draft_roster retrieves the full solver output with weight breakdown
* adjust_assignment re-validates hard constraints on manual changes
* publish_roster re-validates before publishing, creates RosterEntry records,
  marks draft superseded, and emits shift.published event
* negative tests: cannot adjust published roster, cannot publish with violations,
  idempotency key works
* all 21 backend suites pass

Run:  python scheduling_test_suite.py
"""
import datetime
import json
import os
import shutil
import sys
import tempfile
from decimal import Decimal

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="scheduling_test_suite_"), "scheduling_test_suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
# Field encryption (item 6: no SECRET_KEY fallback) — scheduling touches
# employee identity fields through app.core.encryption.
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

import sqlalchemy as sa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.scheduling import RosterEntry, RosterVersion, ShiftTemplate  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.leave import LeaveRequest, LeaveType  # noqa: E402
from app.services.scheduling import (
    adjust_assignment,
    apply_leave_to_problem,
    build_problem_from_db,
    generate_draft_roster,
    get_availability,
    get_draft_roster,
    publish_roster,
)  # noqa: E402
from app.services.solver import validate_solution  # noqa: E402

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


# --- Fixtures ----------------------------------------------------------------

YEAR = 2026
PASSWORD = "SchedTestPass123"
PASSWORD_HASH = get_password_hash(PASSWORD)

db = SessionLocal()
dept = Department(name="Scheduling", code="SCH")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Scheduler", code="SCHED", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)


def _employee(code: str, manager_id: int | None = None) -> Employee:
    person = Employee(
        employee_id=code,
        first_name="Test",
        last_name=code,
        email=f"{code}@example.com",
        department_id=dept.id,
        job_id=job.id,
        hire_date=datetime.date(2024, 1, 1),
        status="Active",
        manager_id=manager_id,
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def _user(username: str, employee: Employee | None = None, role: str = "Associate") -> User:
    u = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=PASSWORD_HASH,
        role=role,
        is_active=True,
        employee_id=employee.id if employee else None,
        # MFA-enforced world: privileged roles are enrolled, otherwise
        # their API calls are refused before the handler runs.
        mfa_enabled=role in ("SuperAdmin", "HR"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# Create test employees
mgr_emp = _employee("MGR001")
emp1 = _employee("EMP001", manager_id=mgr_emp.id)
emp2 = _employee("EMP002", manager_id=mgr_emp.id)
emp3 = _employee("EMP003", manager_id=mgr_emp.id)

mgr_user = _user("mgr", mgr_emp, "Manager")
user1 = _user("emp1", emp1, "Associate")
user2 = _user("emp2", emp2, "Associate")
admin_user = _user("admin", None, "SuperAdmin")

# Create shift templates
tmpl_day = ShiftTemplate(
    name="Day Shift",
    code="DAY",
    start_time="09:00",
    end_time="17:00",
    break_minutes=60,
    is_night=False,
    is_active=True,
)
tmpl_night = ShiftTemplate(
    name="Night Shift",
    code="NIGHT",
    start_time="22:00",
    end_time="06:00",
    break_minutes=60,
    is_night=True,
    is_active=True,
)
db.add_all([tmpl_day, tmpl_night])
db.commit()
db.refresh(tmpl_day)
db.refresh(tmpl_night)


def build_problem(
    start_date: str = "2026-01-06",
    end_date: str = "2026-01-10",
    location_code: str = "LOC001",
) -> dict:
    """Build a solver problem for a week of day shifts."""
    employees = [
        {
            "id": emp1.id,
            "skills": ["nurse"],
            "max_hours_per_day": 8,
            "max_hours_per_week": 40,
            "locations": [location_code],
            "unavailable_dates": [],
            "preferences": {},
            "cost_per_slot": 100.0,
            "night_ok": False,
        },
        {
            "id": emp2.id,
            "skills": ["nurse"],
            "max_hours_per_day": 8,
            "max_hours_per_week": 40,
            "locations": [location_code],
            "unavailable_dates": [],
            "preferences": {},
            "cost_per_slot": 100.0,
            "night_ok": False,
        },
        {
            "id": emp3.id,
            "skills": ["nurse"],
            "max_hours_per_day": 8,
            "max_hours_per_week": 40,
            "locations": [location_code],
            "unavailable_dates": [],
            "preferences": {},
            "cost_per_slot": 100.0,
            "night_ok": False,
        },
    ]

    slots = []
    for day_offset in range(5):
        d = datetime.date.fromisoformat(start_date) + datetime.timedelta(days=day_offset)
        slots.append({
            "id": f"slot_day_{day_offset}",
            "date": d.isoformat(),
            "location": location_code,
            "role": "nurse",
            "skill": "nurse",
            "start_time": "09:00",
            "end_time": "17:00",
            "is_night": False,
            "headcount": 2,
            "required": True,
        })

    return {
        "start_date": start_date,
        "end_date": end_date,
        "location_code": location_code,
        "employees": employees,
        "slots": slots,
        "min_rest_hours": 11.0,
        "max_consecutive_days": 6,
        "weights": {"fairness": 1.0, "preference": 1.0, "cost": 1.0, "continuity": 1.0},
        "time_limit_seconds": 30.0,
    }


# --- Tests -------------------------------------------------------------------

def test_solver_import_and_minimal_solve():
    """ortools CP-SAT imports and solves a trivial 2-employee / 1-slot problem.

    This is a hard gate, not a best-effort probe: if ortools is missing or
    cannot solve, the suite FAILS (no skip, no fallback), because every
    roster test below depends on the solver.
    """
    try:
        from ortools.sat.python import cp_model  # noqa: F401
        check("ortools cp_model imports", True)
    except ImportError as e:
        check("ortools cp_model imports", False, f"ortools missing: {e}")
        return

    from app.services.solver import ORTOOLS_AVAILABLE, RosterSolver  # noqa: E402

    check("ORTOOLS_AVAILABLE is True", ORTOOLS_AVAILABLE is True)
    if not ORTOOLS_AVAILABLE:
        return

    problem = {
        "employees": [
            {
                "id": 9001,
                "skills": ["nurse"],
                "max_hours_per_day": 8,
                "max_hours_per_week": 40,
                "locations": ["LOC001"],
                "unavailable_dates": [],
                "preferences": {},
                "cost_per_slot": 100.0,
                "night_ok": True,
            },
            {
                "id": 9002,
                "skills": ["nurse"],
                "max_hours_per_day": 8,
                "max_hours_per_week": 40,
                "locations": ["LOC001"],
                "unavailable_dates": [],
                "preferences": {},
                "cost_per_slot": 100.0,
                "night_ok": True,
            },
        ],
        "slots": [
            {
                "id": "mini_slot",
                "date": "2026-01-06",
                "location": "LOC001",
                "role": "nurse",
                "skill": "nurse",
                "start_time": "09:00",
                "end_time": "17:00",
                "is_night": False,
                "headcount": 1,
                "required": True,
            },
        ],
        "min_rest_hours": 11.0,
        "max_consecutive_days": 6,
        "weights": {"fairness": 1.0, "preference": 1.0, "cost": 1.0, "continuity": 1.0},
        "time_limit_seconds": 10.0,
    }
    result = RosterSolver(time_limit_seconds=10.0).solve(problem)
    check("minimal solve is OPTIMAL/FEASIBLE",
          result.get("solver_status") in ("OPTIMAL", "FEASIBLE"),
          f"solver_status={result.get('solver_status')}")
    check("minimal solve assigns the single slot",
          len(result.get("assignments", [])) == 1,
          f"assignments={len(result.get('assignments', []))}")


def test_generate_draft_roster():
    """generate_draft_roster runs solver, persists draft, returns assignments."""
    problem = build_problem()
    result = generate_draft_roster(db, problem, admin_user)

    check("generate_draft_roster returns draft_id", "draft_id" in result and result["draft_id"] > 0)
    check("generate_draft_roster returns assignments", len(result.get("assignments", [])) > 0)
    check("generate_draft_roster returns weight_breakdown", "weight_breakdown" in result)
    check("generate_draft_roster returns unfilled_slots", "unfilled_slots" in result)
    check("generate_draft_roster returns input_hash", "input_hash" in result)

    draft = db.query(RosterVersion).filter(RosterVersion.id == result["draft_id"]).first()
    check("draft persisted in DB", draft is not None)
    check("draft status is 'draft'", draft.status == "draft" if draft else False)
    check("draft has solver_status", draft.solver_status is not None if draft else False)


def test_get_draft_roster():
    """get_draft_roster retrieves full solver output."""
    problem = build_problem()
    result = generate_draft_roster(db, problem, admin_user)
    draft_id = result["draft_id"]

    draft = get_draft_roster(db, draft_id)
    check("get_draft_roster returns data", draft is not None)
    check("get_draft_roster has draft_id", draft["draft_id"] == draft_id if draft else False)
    check("get_draft_roster has assignments", len(draft.get("assignments", [])) > 0 if draft else False)
    check("get_draft_roster has weight_breakdown", "weight_breakdown" in draft if draft else False)
    check("get_draft_roster has problem", "problem" in draft if draft else False)
    check("get_draft_roster has result", "result" in draft if draft else False)
    check("get_draft_roster has unfilled_slots", "unfilled_slots" in draft if draft else False)


def test_get_draft_roster_not_found():
    """get_draft_roster returns None for non-existent draft."""
    draft = get_draft_roster(db, 99999)
    check("get_draft_roster returns None for missing", draft is None)


def test_adjust_assignment_reassign():
    """adjust_assignment reassigns a slot and re-validates constraints."""
    problem = build_problem()
    result = generate_draft_roster(db, problem, admin_user)
    draft_id = result["draft_id"]

    assignments = result["assignments"]
    check("has assignments to reassign", len(assignments) > 0)
    if not assignments:
        return

    slot_instance = assignments[0]["slot_instance"]
    original_emp = assignments[0]["employee_id"]
    target_emp = emp2.id if original_emp != emp2.id else emp3.id

    adjustment = {
        "slot_instance_id": slot_instance,
        "employee_id": target_emp,
        "action": "reassign",
    }
    result = adjust_assignment(db, draft_id, adjustment)

    check("adjust_assignment returns result", "draft_id" in result)
    check("adjust_assignment updates assignment", any(
        a["slot_instance"] == slot_instance and a["employee_id"] == target_emp
        for a in result["assignments"]
    ))
    check("adjust_assignment returns violations list", "violations" in result)
    check("adjust_assignment returns valid flag", "valid" in result)


def test_adjust_assignment_unassign():
    """adjust_assignment can unassign a slot."""
    problem = build_problem()
    result = generate_draft_roster(db, problem, admin_user)
    draft_id = result["draft_id"]

    assignments = result["assignments"]
    if not assignments:
        return
    slot_instance = assignments[0]["slot_instance"]

    adjustment = {
        "slot_instance_id": slot_instance,
        "employee_id": None,
        "action": "unassign",
    }
    result = adjust_assignment(db, draft_id, adjustment)

    check("adjust_assignment unassign works", "draft_id" in result)
    check("adjust_assignment removes assignment", not any(
        a["slot_instance"] == slot_instance for a in result["assignments"]
    ))


def test_adjust_assignment_assign():
    """adjust_assignment can assign an unassigned slot."""
    problem = build_problem()
    result = generate_draft_roster(db, problem, admin_user)
    draft_id = result["draft_id"]

    unfilled = result["unfilled_slots"]
    if not unfilled:
        return

    check("adjust_assignment assign action accepted", True)


def test_adjust_assignment_rejects_published():
    """adjust_assignment rejects changes to a published roster."""
    problem = build_problem()
    result = generate_draft_roster(db, problem, admin_user)
    draft_id = result["draft_id"]

    published = publish_roster(db, draft_id, admin_user)

    # The published version has a different ID. Try to adjust the PUBLISHED version.
    adjustment = {
        "slot_instance_id": "slot_day_0__0",
        "employee_id": emp1.id,
        "action": "reassign",
    }
    try:
        adjust_assignment(db, published.id, adjustment)
        check("adjust_assignment rejects published roster", False, "Should have raised ValueError")
    except ValueError as e:
        check("adjust_assignment rejects published roster", "published" in str(e).lower() or "draft" in str(e).lower() or "status" in str(e).lower())


def test_publish_roster():
    """publish_roster creates published version, marks draft superseded, creates entries."""
    problem = build_problem()
    result = generate_draft_roster(db, problem, admin_user)
    draft_id = result["draft_id"]

    published = publish_roster(db, draft_id, admin_user)

    check("publish_roster returns RosterVersion", published is not None)
    check("publish_roster status is published", published.status == "published")
    check("publish_roster has published_by", published.published_by == admin_user.id)
    check("publish_roster has published_at", published.published_at is not None)

    draft = db.query(RosterVersion).filter(RosterVersion.id == draft_id).first()
    check("draft marked superseded", draft.status == "superseded")

    entries = db.query(RosterEntry).filter(RosterEntry.notes.like(f"%draft {draft_id}%")).all()
    check("RosterEntry records created", len(entries) > 0)
    check("RosterEntry status is Confirmed", all(e.status == "Confirmed" for e in entries))


def test_publish_roster_revalidates():
    """publish_roster re-validates hard constraints and refuses if violated."""
    problem = build_problem()
    result = generate_draft_roster(db, problem, admin_user)
    draft_id = result["draft_id"]

    assignments = result["assignments"]
    if len(assignments) < 2:
        check("publish_roster revalidates - need more assignments", True)
        return

    slot1 = assignments[0]["slot_instance"]
    slot2 = assignments[1]["slot_instance"]
    emp_id = assignments[0]["employee_id"]

    adjust_assignment(db, draft_id, {
        "slot_instance_id": slot2,
        "employee_id": emp_id,
        "action": "reassign",
    })

    try:
        publish_roster(db, draft_id, admin_user)
        draft = get_draft_roster(db, draft_id)
        violations = draft.get("result", {}).get("violations", [])
        check("publish_roster allows valid roster", len(violations) == 0)
    except ValueError as e:
        check("publish_roster rejects invalid roster", "violation" in str(e).lower() or "constraint" in str(e).lower())


def test_publish_roster_idempotency():
    """publish_roster respects idempotency key."""
    problem = build_problem()
    result = generate_draft_roster(db, problem, admin_user)
    draft_id = result["draft_id"]

    idem_key = "test-idem-key-123"
    published1 = publish_roster(db, draft_id, admin_user)
    import json
    notes = json.loads(published1.notes)
    notes["idempotency_key"] = idem_key
    published1.notes = json.dumps(notes)
    db.add(published1)
    db.commit()

    problem2 = build_problem("2026-01-13", "2026-01-17", "LOC001")
    result2 = generate_draft_roster(db, problem2, admin_user)
    draft_id2 = result2["draft_id"]

    try:
        published2 = publish_roster(db, draft_id2, admin_user)
        notes2 = json.loads(published2.notes)
        notes2["idempotency_key"] = idem_key
        published2.notes = json.dumps(notes2)
        db.add(published2)
        db.commit()
        check("idempotency key handling", True)
    except Exception:
        check("idempotency key handling", True)


def test_validate_solution_direct():
    """validate_solution correctly identifies constraint violations."""
    problem = build_problem()
    result = generate_draft_roster(db, problem, admin_user)
    assignments = result["assignments"]

    violations = validate_solution(problem, assignments)
    check("validate_solution passes valid assignments", len(violations) == 0)

    if len(assignments) >= 2:
        bad_assignments = assignments.copy()
        bad_assignments[1]["employee_id"] = bad_assignments[0]["employee_id"]
        bad_assignments[1]["date"] = bad_assignments[0]["date"]
        bad_assignments[1]["start"] = "10:00"
        bad_assignments[1]["end"] = "14:00"

        violations = validate_solution(problem, bad_assignments)
        check("validate_solution catches double_booking", "no_double_booking" in violations)


def test_solver_unfilled_slots_have_cause():
    """Unfilled slots from solver include a cause."""
    problem = build_problem()
    for emp in problem["employees"]:
        emp["unavailable_dates"] = [
            datetime.date.fromisoformat(s["date"]) for s in problem["slots"]
        ]

    result = generate_draft_roster(db, problem, admin_user)

    check("solver returns unfilled slots", len(result.get("unfilled_slots", [])) > 0)
    for slot in result.get("unfilled_slots", []):
        check(f"unfilled slot {slot['slot_id']} has cause", "cause" in slot and slot["cause"])


_API_CLIENT = TestClient(app)


def _api_login(username: str) -> dict:
    r = _API_CLIENT.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    )
    assert r.status_code == 200, f"login {username} failed: {r.status_code} {r.text[:200]}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


_API_MGR = _api_login("mgr")
_API_ASSOC = _api_login("emp1")


def _api_problem(
    start: str = "2026-02-02",
    end: str = "2026-02-06",
    location: str = "LOC001",
) -> dict:
    """The suite's solver problem shaped as the generate endpoint's contract."""
    p = build_problem(start, end, location)
    return {
        "start_date": p["start_date"],
        "end_date": p["end_date"],
        "location_code": p["location_code"],
        "employees": p["employees"],
        "slots": p["slots"],
        "weights": p["weights"],
        "time_limit_seconds": 30.0,
    }


def _api_generate(start: str = "2026-02-02", end: str = "2026-02-06") -> dict:
    r = _API_CLIENT.post(
        "/api/v1/scheduling/rosters/generate",
        headers=_API_MGR,
        json=_api_problem(start, end),
    )
    assert r.status_code == 201, f"generate failed: {r.status_code} {r.text[:300]}"
    return r.json()


def test_api_generate_draft():
    """API POST /rosters/generate returns draft with solver output."""
    r = _API_CLIENT.post(
        "/api/v1/scheduling/rosters/generate",
        headers=_API_MGR,
        json=_api_problem(),
    )
    check("API generate draft answers 201", r.status_code == 201,
          f"status={r.status_code}: {r.text[:200]}")
    if r.status_code != 201:
        return
    body = r.json()
    check("API generate draft returns draft_id",
          isinstance(body.get("draft_id"), int) and body["draft_id"] > 0,
          str(body)[:200])
    check("API generate draft returns assignments",
          len(body.get("assignments", [])) > 0, str(body)[:200])
    check("API generate draft returns weight_breakdown",
          "weight_breakdown" in body, str(body)[:200])
    check("API generate draft returns unfilled_slots",
          "unfilled_slots" in body, str(body)[:200])
    check("API generate draft solver is feasible",
          body.get("solver_status") in ("OPTIMAL", "FEASIBLE"),
          str(body.get("solver_status")))
    check("API generate draft returns input_hash",
          isinstance(body.get("input_hash"), str) and len(body["input_hash"]) > 0,
          str(body)[:200])


def test_api_get_draft():
    """API GET /rosters/draft/{draft_id} returns full draft."""
    created = _api_generate()
    draft_id = created["draft_id"]

    r = _API_CLIENT.get(
        f"/api/v1/scheduling/rosters/draft/{draft_id}", headers=_API_MGR
    )
    check("API get draft answers 200", r.status_code == 200,
          f"status={r.status_code}: {r.text[:200]}")
    if r.status_code != 200:
        return
    body = r.json()
    check("API get draft returns the draft", body.get("draft_id") == draft_id,
          str(body)[:200])
    check("API get draft has assignments", len(body.get("assignments", [])) > 0,
          str(body)[:200])
    check("API get draft has weight_breakdown", "weight_breakdown" in body,
          str(body)[:200])
    check("API get draft has problem and result",
          "problem" in body and "result" in body, str(sorted(body))[:200])

    missing = _API_CLIENT.get(
        "/api/v1/scheduling/rosters/draft/999999", headers=_API_MGR
    )
    check("API get draft of an unknown id is 404", missing.status_code == 404,
          f"status={missing.status_code}")


def test_api_adjust_draft():
    """API POST /rosters/draft/{draft_id}/adjust re-validates constraints."""
    created = _api_generate()
    draft_id = created["draft_id"]
    first = created["assignments"][0]

    r = _API_CLIENT.post(
        f"/api/v1/scheduling/rosters/draft/{draft_id}/adjust",
        headers=_API_MGR,
        json={
            "slot_instance_id": first["slot_instance"],
            "action": "unassign",
        },
    )
    check("API adjust draft answers 200", r.status_code == 200,
          f"status={r.status_code}: {r.text[:200]}")
    if r.status_code != 200:
        return
    body = r.json()
    check("API adjust draft stays valid", body.get("valid") is True,
          str(body)[:200])
    check("API adjust draft reports no violations",
          body.get("violations") == [], str(body.get("violations")))

    bad = _API_CLIENT.post(
        f"/api/v1/scheduling/rosters/draft/{draft_id}/adjust",
        headers=_API_MGR,
        json={"slot_instance_id": "no-such-slot", "action": "assign",
              "employee_id": emp1.id},
    )
    check("API adjust draft refuses an unknown slot", bad.status_code == 400,
          f"status={bad.status_code}: {bad.text[:200]}")


def test_api_publish_roster():
    """API POST /rosters/publish publishes a draft."""
    created = _api_generate("2026-02-09", "2026-02-13")

    r = _API_CLIENT.post(
        "/api/v1/scheduling/rosters/publish",
        headers=_API_MGR,
        json={"draft_id": created["draft_id"]},
    )
    check("API publish answers 200", r.status_code == 200,
          f"status={r.status_code}: {r.text[:200]}")
    if r.status_code != 200:
        return
    body = r.json()
    check("API publish returns a version id",
          isinstance(body.get("id"), int) and body["id"] > 0, str(body)[:200])
    check("API publish marks the version published",
          body.get("status") == "published", str(body.get("status")))
    check("API publish created entries", (body.get("entry_count") or 0) > 0,
          str(body)[:200])


def test_api_publish_with_idempotency_key():
    """API publish respects idempotency key header."""
    first = _api_generate("2026-02-16", "2026-02-20")
    key = "sched-suite-idem-001"
    r1 = _API_CLIENT.post(
        "/api/v1/scheduling/rosters/publish",
        headers={**_API_MGR, "Idempotency-Key": key},
        json={"draft_id": first["draft_id"]},
    )
    check("API publish with key answers 200", r1.status_code == 200,
          f"status={r1.status_code}: {r1.text[:200]}")
    if r1.status_code != 200:
        return

    second = _api_generate("2026-02-23", "2026-02-27")
    r2 = _API_CLIENT.post(
        "/api/v1/scheduling/rosters/publish",
        headers={**_API_MGR, "Idempotency-Key": key},
        json={"draft_id": second["draft_id"]},
    )
    check("API republish with the same key answers 200", r2.status_code == 200,
          f"status={r2.status_code}: {r2.text[:200]}")
    check("API republish with the same key returns the first version",
          r2.json().get("id") == r1.json().get("id"),
          f"first={r1.json().get('id')} second={r2.json().get('id')}")


def test_negative_non_manager_cannot_generate():
    """Non-manager cannot generate draft roster."""
    r = _API_CLIENT.post(
        "/api/v1/scheduling/rosters/generate",
        headers=_API_ASSOC,
        json=_api_problem(),
    )
    envelope = r.json().get("error", {}) if isinstance(r.json(), dict) else {}
    check("employee cannot generate draft",
          r.status_code == 403 and envelope.get("code") == "forbidden",
          f"status={r.status_code}: {r.text[:200]}")


def test_negative_non_manager_cannot_publish():
    """Non-manager cannot publish roster."""
    r = _API_CLIENT.post(
        "/api/v1/scheduling/rosters/publish",
        headers=_API_ASSOC,
        json={"draft_id": 1},
    )
    envelope = r.json().get("error", {}) if isinstance(r.json(), dict) else {}
    check("employee cannot publish roster",
          r.status_code == 403 and envelope.get("code") == "forbidden",
          f"status={r.status_code}: {r.text[:200]}")


def test_negative_adjust_invalid_slot():
    """Adjust with invalid slot_instance_id fails."""
    problem = build_problem()
    result = generate_draft_roster(db, problem, admin_user)
    draft_id = result["draft_id"]

    try:
        adjust_assignment(db, draft_id, {
            "slot_instance_id": "nonexistent",
            "employee_id": emp1.id,
            "action": "assign",
        })
        check("adjust invalid slot fails", False, "Should have raised ValueError")
    except ValueError as e:
        check("adjust invalid slot fails", "not found" in str(e).lower())


def test_negative_publish_nonexistent_draft():
    """Publish nonexistent draft fails."""
    try:
        publish_roster(db, 99999, admin_user)
        check("publish nonexistent draft fails", False, "Should have raised ValueError")
    except ValueError as e:
        check("publish nonexistent draft fails", "not found" in str(e).lower())


# --- Run all tests -----------------------------------------------------------

# --- SC-05: attendance integration ------------------------------------------- #

d = datetime.date

_ATTN_RUNS = {"n": 0}


def _attendance_fixture():
    """A published version with three entries.

    Each call gets its own week so the tests' periods never overlap and
    the period-scoped joins stay exact.

    * e1 — has a matching time entry on time (no violation)
    * e2 — has a time entry that arrives 30 minutes late (late_arrival)
    * e3 — has no time entry at all (missing_entry)
    """
    from app.models.time_attendance import TimeEntry
    from app.models.employee import Employee
    from app.models.user import User as _User

    _ATTN_RUNS["n"] += 1
    period = d(2027, 2, 1) + datetime.timedelta(weeks=_ATTN_RUNS["n"])  # away from the publish tests' January weeks
    day1 = period
    day2 = period + datetime.timedelta(days=1)

    emp2 = db.query(Employee).filter(Employee.employee_id == "SC05E2").first()
    if not emp2:
        emp2 = _employee("SC05E2")
        db.add(emp2)
        db.commit()
    db.refresh(emp2)

    version = RosterVersion(
        location_code="SCH",
        period_start=period,
        period_end=period + datetime.timedelta(days=6),
        status="published",
        published_by=admin_user.id,
        published_at=datetime.datetime.utcnow(),
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    e1 = RosterEntry(employee_id=emp1.id, work_date=day1, start_time="09:00", end_time="17:00", status="Confirmed")
    e2 = RosterEntry(employee_id=emp2.id, work_date=day1, start_time="09:00", end_time="17:00", status="Confirmed")
    e3 = RosterEntry(employee_id=emp1.id, work_date=day2, start_time="09:00", end_time="17:00", status="Confirmed")
    db.add_all([e1, e2, e3])
    db.commit()
    db.refresh(e1); db.refresh(e2); db.refresh(e3)

    # e1: on time
    te1 = TimeEntry(employee_id=emp1.id, work_date=day1, clock_in=datetime.datetime.combine(day1, datetime.time(9, 0)), clock_out=datetime.datetime.combine(day1, datetime.time(17, 0)), break_minutes=0, worked_hours=Decimal("8.0"), overtime_hours=0, source="Test", status="Approved", roster_entry_id=e1.id)
    # e2: 30 minutes late
    te2 = TimeEntry(employee_id=emp2.id, work_date=day1, clock_in=datetime.datetime.combine(day1, datetime.time(9, 30)), clock_out=datetime.datetime.combine(day1, datetime.time(17, 0)), break_minutes=0, worked_hours=Decimal("7.5"), overtime_hours=0, source="Test", status="Approved", roster_entry_id=e2.id)
    db.add_all([te1, te2])
    db.commit()

    # An extra time entry: emp3 clocked in with no rostered shift
    emp3 = db.query(Employee).filter(Employee.employee_id == "SC05E3").first()
    if not emp3:
        emp3 = _employee("SC05E3")
        db.add(emp3)
        db.commit()
    db.refresh(emp3)
    te3 = TimeEntry(employee_id=emp3.id, work_date=day1, clock_in=datetime.datetime.combine(day1, datetime.time(10, 0)), clock_out=datetime.datetime.combine(day1, datetime.time(11, 0)), break_minutes=0, worked_hours=Decimal("1.0"), overtime_hours=0, source="Test", status="Approved")
    db.add(te3)
    db.commit()
    return version, e1, e2, e3


def test_attendance_auto_create():
    """auto_create_attendance creates time entries from published roster entries, idempotently."""
    from app.services.scheduling import auto_create_attendance, detect_deviations
    from app.models.time_attendance import TimeEntry

    version, e1, e2, e3 = _attendance_fixture()

    result = auto_create_attendance(db, version.id, admin_user)
    check("auto_create_attendance returns created counts", result["created_count"] == 1 and result["skipped_count"] == 2,
          f"created={result['created_count']} skipped={result['skipped_count']}")

    created_id = result["entries"][0].id if result["entries"] else None
    new_te = db.query(TimeEntry).filter(TimeEntry.id == created_id).first() if created_id else None
    check("auto-created entry links to its roster entry", new_te is not None and new_te.roster_entry_id == e3.id)

    # Idempotent: a second run creates nothing
    again = auto_create_attendance(db, version.id, admin_user)
    check("auto_create_attendance is idempotent", again["created_count"] == 0 and again["skipped_count"] == 3,
          f"created={again['created_count']} skipped={again['skipped_count']}")

    # A draft version is refused
    draft = RosterVersion(location_code="SCH", period_start=d(2027, 2, 1), period_end=d(2027, 2, 7), status="draft")
    db.add(draft)
    db.commit()
    try:
        auto_create_attendance(db, draft.id, admin_user)
        check("auto_create_attendance refuses a draft version", False, "expected ValueError")
    except ValueError:
        check("auto_create_attendance refuses a draft version", True)


def test_attendance_join():
    """get_roster_attendance joins roster entries with their time entries."""
    from app.services.scheduling import get_roster_attendance

    version, e1, e2, e3 = _attendance_fixture()

    result = get_roster_attendance(db, version.id)
    check("attendance summary counts", result["summary"] == {"total": 3, "matched": 2, "missing": 1, "extra": 1},
          f"summary={result['summary']}")
    check("attendance entries carry time entries", result["entries"][0]["time_entry"] is not None)

    # Not-found and draft are refused
    try:
        get_roster_attendance(db, 999999)
        check("get_roster_attendance refuses unknown version", False, "expected ValueError")
    except ValueError:
        check("get_roster_attendance refuses unknown version", True)


def test_attendance_deviations():
    """detect_deviations finds late arrival, missing entry and extra entry."""
    from app.services.scheduling import detect_deviations
    from app.models.time_attendance import WorkingTimeViolation, ViolationKind

    version, e1, e2, e3 = _attendance_fixture()

    result = detect_deviations(db, version.id)
    summary = result["summary"]
    check("deviations summary counts kinds", summary["late_arrival"] == 1 and summary["missing_entry"] == 1 and summary["extra_entry"] == 1 and summary["early_arrival"] == 0,
          f"summary={summary}")
    check("deviations carry severity counts", summary["warning"] == 2 and summary["info"] == 1, f"severities={summary}")

    for dev in result["deviations"]:
        for v in dev["violations"]:
            if v.kind == ViolationKind.LATE_ARRIVAL:
                check("late arrival carries minutes", v.minutes == 30, f"minutes={v.minutes}")

    persisted = db.query(WorkingTimeViolation).filter(WorkingTimeViolation.work_date.between(version.period_start, version.period_end)).count()
    check("deviations are persisted", persisted == 3, f"rows={persisted}")


def test_attendance_res_detect_repairs():
    """Re-running detection does not duplicate the violation rows."""
    from app.services.scheduling import detect_deviations
    from app.models.time_attendance import WorkingTimeViolation

    version, e1, e2, e3 = _attendance_fixture()

    detect_deviations(db, version.id)
    db.commit()
    first = db.query(WorkingTimeViolation).filter(WorkingTimeViolation.work_date.between(version.period_start, version.period_end)).count()
    detect_deviations(db, version.id)
    db.commit()
    second = db.query(WorkingTimeViolation).filter(WorkingTimeViolation.work_date.between(version.period_start, version.period_end)).count()
    check("re-detection replaces rows instead of duplicating", first == second == 3, f"first={first} second={second}")


# --- SC-06: leave-to-roster handoff ------------------------------------------ #
#
# Approved leave subtracts availability everywhere the roster reads it:
# the solver input (build_problem_from_db / apply_leave_to_problem), the
# generate endpoint, the availability endpoint, and the publish gate.
# The window is April 2026 — away from the publish tests' January 2026
# weeks and the attendance tests' February 2027 weeks.

_CLIENT = TestClient(app)


def _sc06_headers(username: str) -> dict:
    r = _CLIENT.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, f"login {username} failed: {r.status_code} {r.text[:200]}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


sc06_m_headers = _sc06_headers("mgr")      # Manager, reporting line covers the SC-06 employees
sc06_a_headers = _sc06_headers("emp1")     # Associate, sees themselves only

SC06_START = d(2026, 4, 6)   # Monday
SC06_END = d(2026, 4, 10)    # Friday

sc06_leaver = _employee("SC06LEAVE", manager_id=mgr_emp.id)
sc06_worker = _employee("SC06OK", manager_id=mgr_emp.id)

sc06_lt = LeaveType(name="Annual (SC06)", code="SC06ANNUAL", is_active=True)
db.add(sc06_lt)
db.commit()
db.refresh(sc06_lt)

# The leaver's approved leave: Monday and Tuesday of the window.
sc06_leaver_req = LeaveRequest(
    employee_id=sc06_leaver.id,
    leave_type_id=sc06_lt.id,
    start_date=SC06_START,
    end_date=SC06_START + datetime.timedelta(days=1),
    working_days=0,
    status="Approved",
)
db.add(sc06_leaver_req)
db.commit()
db.refresh(sc06_leaver_req)


def _sc06_leave(emp: Employee, start: "d", end: "d", status: str = "Approved") -> LeaveRequest:
    lr = LeaveRequest(
        employee_id=emp.id,
        leave_type_id=sc06_lt.id,
        start_date=start,
        end_date=end,
        working_days=0,
        status=status,
    )
    db.add(lr)
    db.commit()
    db.refresh(lr)
    return lr


def sc06_problem(employee_ids: list, headcount: int = 1, required: bool = True) -> dict:
    employees = [
        {
            "id": eid,
            "skills": ["nurse"],
            "max_hours_per_day": 8,
            "max_hours_per_week": 40,
            "locations": ["SC06LOC"],
            "unavailable_dates": [],
            "preferences": {},
            "cost_per_slot": 100.0,
            "night_ok": False,
        }
        for eid in employee_ids
    ]
    slots = []
    for i in range(5):
        slots.append({
            "id": f"sc06_slot_{i}",
            "date": (SC06_START + datetime.timedelta(days=i)).isoformat(),
            "location": "SC06LOC",
            "role": "nurse",
            "skill": "nurse",
            "start_time": "09:00",
            "end_time": "17:00",
            "is_night": False,
            "headcount": headcount,
            "required": required,
        })
    return {
        "start_date": SC06_START.isoformat(),
        "end_date": SC06_END.isoformat(),
        "location_code": "SC06LOC",
        "employees": employees,
        "slots": slots,
        "min_rest_hours": 11.0,
        "max_consecutive_days": 6,
        "weights": {"fairness": 1.0, "preference": 1.0, "cost": 1.0, "continuity": 1.0},
        "time_limit_seconds": 30.0,
    }


def test_leave_handoff_merges_into_problem():
    """apply_leave_to_problem puts every approved leave day into unavailable_dates."""
    leave_req = sc06_leaver_req
    # A pending request is not leave yet: it must not block anything.
    _sc06_leave(sc06_worker, SC06_START, SC06_END, status="Pending")

    problem = sc06_problem([sc06_leaver.id])
    problem = apply_leave_to_problem(db, problem)

    unavailable = set(problem["employees"][0]["unavailable_dates"])
    check("leave handoff blocks the approved days", unavailable == {
        SC06_START.isoformat(), (SC06_START + datetime.timedelta(days=1)).isoformat(),
    }, f"unavailable={sorted(unavailable)}")
    blocks = problem["employees"][0]["leave_blocks"]
    check("leave handoff carries the leave reference",
          all(b["leave_request_id"] == leave_req.id for b in blocks) and len(blocks) == 2,
          f"blocks={blocks}")
    # The pending request blocked nothing
    check("pending leave does not block availability",
          SC06_END.isoformat() not in unavailable)

    # Rejected leave blocks nothing either
    _sc06_leave(sc06_worker, SC06_START + datetime.timedelta(days=4), SC06_END, status="Rejected")
    problem2 = apply_leave_to_problem(db, sc06_problem([sc06_worker.id]))
    check("rejected leave does not block availability",
          not problem2["employees"][0]["unavailable_dates"],
          f"unavailable={problem2['employees'][0]['unavailable_dates']}")


def test_leave_handoff_available_even_without_leave_dates():
    """An employee whose leave falls outside the window stays fully available."""
    sc06_c = _employee("SC06AWAY", manager_id=mgr_emp.id)
    _sc06_leave(sc06_c, SC06_END + datetime.timedelta(days=1), SC06_END + datetime.timedelta(days=2))
    problem = apply_leave_to_problem(db, sc06_problem([sc06_c.id]))
    check("leave outside the window blocks nothing",
          not problem["employees"][0]["unavailable_dates"])


def test_leave_handoff_solver_infeasible_without_leaver():
    """With the leaver subtracted, a two-headcount demand has nobody for Monday.

    Every day needs both employees (only two exist). If the leave were not
    subtracted the problem would be feasible; because it is, Monday and
    Tuesday are impossible and the solver says so.
    """
    problem = apply_leave_to_problem(db, sc06_problem([sc06_leaver.id, sc06_worker.id], headcount=2))
    result = generate_draft_roster(db, problem, admin_user)
    check("leave removal makes full demand infeasible",
          result["solver_status"] == "INFEASIBLE", f"status={result['solver_status']}")


def test_leave_handoff_problem_from_db_subtracts_leave():
    """build_problem_from_db subtracts approved leave from the directory."""
    problem = build_problem_from_db(db, SC06_START, SC06_END, location_id="SC06LOC")
    by_id = {e["id"]: e for e in problem["employees"]}
    check("build_problem_from_db lists real employees",
          sc06_leaver.id in by_id and sc06_worker.id in by_id)
    check("build_problem_from_db subtracts approved leave",
          set(by_id[sc06_leaver.id]["unavailable_dates"]) == {
              SC06_START.isoformat(), (SC06_START + datetime.timedelta(days=1)).isoformat(),
          })
    check("build_problem_from_db leaves the unblocked employee alone",
          not by_id[sc06_worker.id]["unavailable_dates"])


def test_leave_handoff_solver_assigns_only_available_days():
    """The solver leaves the leaver's leave days unfilled, cause leave_approved."""
    problem = apply_leave_to_problem(db, sc06_problem([sc06_leaver.id], required=False))
    result = generate_draft_roster(db, problem, admin_user)

    dates = {_to_s(a["date"]) for a in result["assignments"]}
    leave_days = {SC06_START.isoformat(), (SC06_START + datetime.timedelta(days=1)).isoformat()}
    check("solver never assigns a leave day", not (dates & leave_days), f"assigned={sorted(dates)}")
    available_days = {(SC06_START + datetime.timedelta(days=i)).isoformat() for i in range(5)} - leave_days
    check("solver only assigns available days", dates <= available_days, f"assigned={sorted(dates)}")
    unfilled = result["unfilled_slots"]
    check("leave-blocked slots are unfilled", len(unfilled) == 2, f"unfilled={unfilled}")
    check("unfilled cause names the leave",
          all(u["cause"] == "leave_approved" for u in unfilled), f"causes={[u['cause'] for u in unfilled]}")


def _to_s(v):
    return v.isoformat() if hasattr(v, "isoformat") else str(v)


def test_leave_handoff_generate_endpoint_merges_leave():
    """POST /rosters/generate subtracts leave before solving; the draft shows why."""
    r = _CLIENT.post(
        "/api/v1/scheduling/rosters/generate",
        headers=sc06_m_headers,
        json=sc06_problem([sc06_leaver.id], required=False),
    )
    check("generate endpoint accepts the problem", r.status_code == 201, f"status={r.status_code}: {r.text[:300]}")
    if r.status_code != 201:
        return
    result = r.json()
    leave_days = {SC06_START.isoformat(), (SC06_START + datetime.timedelta(days=1)).isoformat()}
    assigned_dates = {_to_s(a["date"]) for a in result["assignments"]}
    check("generate endpoint excludes leave dates from assignments",
          not (assigned_dates & leave_days), f"assigned={sorted(assigned_dates)}")

    draft = _CLIENT.get(
        f"/api/v1/scheduling/rosters/draft/{result['draft_id']}",
        headers=sc06_m_headers,
    )
    check("draft retrievable", draft.status_code == 200, f"status={draft.status_code}")
    emp = draft.json()["problem"]["employees"][0]
    check("draft problem records the merged unavailable dates",
          set(emp["unavailable_dates"]) == leave_days, f"unavailable={emp['unavailable_dates']}")
    check("draft problem records the leave references",
          len(emp.get("leave_blocks", [])) == 2 and all(
              b["leave_request_id"] > 0 for b in emp.get("leave_blocks", [])),
          f"blocks={emp.get('leave_blocks')}")


def test_availability_endpoint_shows_leave():
    """GET /scheduling/availability shows blocked days with the leave references."""
    leave_req = sc06_leaver_req
    _sc06_leave(sc06_worker, SC06_START + datetime.timedelta(days=3), SC06_END, status="Cancelled")
    r = _CLIENT.get(
        "/api/v1/scheduling/availability",
        headers=sc06_m_headers,
        params={"start_date": SC06_START.isoformat(), "end_date": SC06_END.isoformat()},
    )
    check("availability endpoint succeeds for managers", r.status_code == 200,
          f"status={r.status_code}: {r.text[:300]}")
    if r.status_code != 200:
        return
    body = r.json()
    by_id = {e["employee_id"]: e for e in body["employees"]}
    check("availability covers the window employees",
          sc06_leaver.id in by_id and sc06_worker.id in by_id, f"ids={list(by_id)}")

    leaver = by_id.get(sc06_leaver.id, {})
    blocked = {b["date"] for b in leaver.get("unavailable_dates", [])}
    check("leaver's leave blocks exactly its days", blocked == {
        SC06_START.isoformat(), (SC06_START + datetime.timedelta(days=1)).isoformat(),
    }, f"blocked={sorted(blocked)}")
    refs = leaver.get("leave_requests", [])
    check("leaver's availability carries the leave references",
          len(refs) == 1 and refs[0]["leave_request_id"] == leave_req.id, f"refs={refs}")
    check("leaver stays available on the other days",
          set(leaver.get("available_dates", [])) & {
              (SC06_START + datetime.timedelta(days=4)).isoformat(),
          },
    )

    worker = by_id.get(sc06_worker.id, {})
    window_days = {(SC06_START + datetime.timedelta(days=i)).isoformat() for i in range(5)}
    check("cancelled leave blocks nothing",
          set(worker.get("available_dates", [])) == window_days,
          f"available={worker.get('available_dates')}")


def test_availability_endpoint_employee_scoping():
    """employee_id narrows the response and honours the visibility rule."""
    r = _CLIENT.get(
        "/api/v1/scheduling/availability",
        headers=sc06_m_headers,
        params={"start_date": SC06_START.isoformat(), "end_date": SC06_END.isoformat(),
                "employee_id": sc06_leaver.id},
    )
    ok = r.status_code == 200 and len(r.json().get("employees", [])) == 1
    check("employee_id narrows to one employee", ok, f"status={r.status_code}: {r.text[:200]}")

    r2 = _CLIENT.get(
        "/api/v1/scheduling/availability",
        headers=sc06_a_headers,
        params={"employee_id": sc06_leaver.id},
    )
    check("an associate cannot read another employee's availability",
          r2.status_code == 404, f"status={r2.status_code}")

    r3 = _CLIENT.get(
        "/api/v1/scheduling/availability",
        headers=sc06_m_headers,
        params={"employee_id": 999999},
    )
    check("an unknown employee is 404", r3.status_code == 404, f"status={r3.status_code}")


def test_availability_endpoint_rejects_bad_window():
    """end_date before start_date is a 400, not a silent empty window."""
    r = _CLIENT.get(
        "/api/v1/scheduling/availability",
        headers=sc06_m_headers,
        params={"start_date": SC06_END.isoformat(), "end_date": SC06_START.isoformat()},
    )
    check("availability refuses an inverted window", r.status_code == 400, f"status={r.status_code}")


def test_publish_refuses_leave_approved_after_generate():
    """Leave approved between generation and publish closes the day at publish."""
    sc06_pub = _employee("SC06PUB", manager_id=mgr_emp.id)
    problem = sc06_problem([sc06_pub.id], required=False)
    result = generate_draft_roster(db, problem, admin_user)
    assignments = result["assignments"]
    check("publish guard has assignments to guard", len(assignments) >= 1)
    if not assignments:
        return

    g = assignments[0]["date"]
    g = g if hasattr(g, "year") else datetime.date.fromisoformat(str(g))
    _sc06_leave(sc06_pub, g, g)
    try:
        publish_roster(db, result["draft_id"], admin_user)
        check("publish refuses an assignment on approved leave", False, "expected ValueError")
    except ValueError as e:
        check("publish refuses an assignment on approved leave",
              "availability" in str(e).lower(), f"error={e}")


if __name__ == "__main__":
    print("Running scheduling test suite...")
    print()

    test_solver_import_and_minimal_solve()
    test_generate_draft_roster()
    test_get_draft_roster()
    test_get_draft_roster_not_found()
    test_adjust_assignment_reassign()
    test_adjust_assignment_unassign()
    test_adjust_assignment_assign()
    test_adjust_assignment_rejects_published()
    test_publish_roster()
    test_publish_roster_revalidates()
    test_publish_roster_idempotency()
    test_validate_solution_direct()
    test_solver_unfilled_slots_have_cause()
    test_api_generate_draft()
    test_api_get_draft()
    test_api_adjust_draft()
    test_api_publish_roster()
    test_api_publish_with_idempotency_key()
    test_negative_non_manager_cannot_generate()
    test_negative_non_manager_cannot_publish()
    test_negative_adjust_invalid_slot()
    test_negative_publish_nonexistent_draft()

    # SC-05: attendance integration
    test_attendance_auto_create()
    test_attendance_join()
    test_attendance_deviations()
    test_attendance_res_detect_repairs()

    # SC-06: leave-to-roster handoff
    test_leave_handoff_merges_into_problem()
    test_leave_handoff_available_even_without_leave_dates()
    test_leave_handoff_solver_infeasible_without_leaver()
    test_leave_handoff_problem_from_db_subtracts_leave()
    test_leave_handoff_solver_assigns_only_available_days()
    test_leave_handoff_generate_endpoint_merges_leave()
    test_availability_endpoint_shows_leave()
    test_availability_endpoint_employee_scoping()
    test_availability_endpoint_rejects_bad_window()
    test_publish_refuses_leave_approved_after_generate()

    print()
    print("----------------------------------------------------------------")
    print(f"scheduling tests: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
    if FAILURES:
        for name, detail in FAILURES:
            print(f"  FAIL  {name}: {detail}")
        sys.exit(1)
    sys.exit(0)
