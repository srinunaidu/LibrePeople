#!/usr/bin/env python3
"""
Karmathy HCM — deterministic synthetic seed generator.

Usage (from repo root):

    python -m seed.dev.seed_dev

Generates synthetic demo data for a local or staging database. Refuses to run
against a production (Oracle / remote) target.

The seed is deterministic (fixed random seed) and idempotent: re-running does
not duplicate rows.

All personal data is synthetic: names from a fictional word list, emails on
the reserved ``.test`` domain, salaries as random numbers within bands, and
IDs as placeholders.

Credentials for generated accounts are written to a git-ignored local file
(``seed/dev/.credentials.out``) and never printed to stdout or committed.
"""
from __future__ import annotations

import json
import os
import random
import string
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

# Allow running as `python -m seed.dev.seed_dev` from repo root.
# The `app` package lives under `backend/`.
backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))
os.chdir(backend_path)  # Change to backend dir so .env is found

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models import (  # noqa: F401  (register all models on Base.metadata)
    audit,
    benefits,
    client_onboarding,
    compliance,
    core_hr,
    department,
    employee,
    ess_hr,
    integrations_platform,
    job,
    learning,
    leave,
    offboarding,
    onboarding,
    payroll,
    performance,
    recruiting,
    refresh_token,
    scheduling,
    time_attendance,
    user,
)
from app.models.base import Base
from app.models.core_hr import Location
from app.models.department import Department
from app.models.employee import Employee
from app.models.job import Job
from app.models.leave import LeaveBalance, LeaveRequest, LeaveType
from app.models.payroll import (
    EmployeePayProfile,
    PayComponent,
    PayRun,
    PaySlip,
)
from app.models.refresh_token import RefreshToken
from app.models.scheduling import RosterEntry, ShiftTemplate
from app.models.user import User
from app.models.time_attendance import TimeEntry

RANDOM_SEED = 424242
EMAIL_DOMAIN = "example.test"
CREDENTIALS_OUT = Path(__file__).resolve().parent / ".credentials.out"

LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

rng = random.Random(RANDOM_SEED)

FIRST_NAMES = [
    "Aarav", "Bimala", "Chidi", "Dina", "Elio", "Fatima", "Ganesh", "Hina",
    "Imani", "Jules", "Kiran", "Lina", "Mateo", "Nia", "Omar", "Priya",
    "Quinn", "Ravi", "Sora", "Tariq", "Uma", "Victor", "Wren", "Xavi", "Yara", "Zane",
]
LAST_NAMES = [
    "Alvaro", "Bennett", "Chowdhury", "Dubois", "Eze", "Fernandez", "Gomez",
    "Hassan", "Ibrahim", "Johnson", "Kumar", "Lopez", "Mbeki", "Nguyen",
    "Okafor", "Petrov", "Quinn", "Rossi", "Singh", "Tanaka", "Ukpabi", "Vega",
    "Wang", "Xu", "Yilmaz", "Zahir",
]


#: The scratch schema the staging gate owns (`scripts/staging/run.sh`). A
#: remote target is refused unless the operator names *this* schema in
#: `KARMA_SEED_TARGET` and the URL's schema component matches it exactly.
#: Production schema names are refused even then — the allowlist is wide
#: enough for staging and no wider.
STAGING_TARGETS = {"karma_stage"}
REFUSED_SCHEMAS = {"admin", "prod", "production", "live", "karmathy_admin", "karmathy_prod"}


def _target_schema(database_url: str) -> str | None:
    """The schema component of an oracle+oracledb:// URL, if one is present."""
    dl = database_url.lower()
    if not dl.startswith("oracle+"):
        return None
    tail = dl.split("://", 1)[1] if "://" in dl else ""
    return tail.split("/", 1)[1] if "/" in tail else (tail or None)


def _is_production_target(database_url: str) -> bool:
    dl = database_url.lower()
    if dl.startswith("oracle+"):
        schema = _target_schema(database_url)
        if schema in REFUSED_SCHEMAS:
            return True
        allowed = os.environ.get("KARMA_SEED_TARGET", "").strip().lower()
        return not (allowed in STAGING_TARGETS and schema == allowed)
    if "@" in dl:
        host_part = dl.split("@", 1)[1].split("/", 1)[0]
        host = host_part.split(":")[0]
        if host not in LOCAL_HOSTS:
            return True
    return False


def _resolve_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        url = "sqlite:///" + str(
            Path(__file__).resolve().parent.parent.parent / "seed_dev.db"
        )
    return url


def _name() -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _email(first: str, last: str, idx: int, prefix: str = "") -> str:
    return f"{prefix}.{first.lower()}.{last.lower()}{idx}@{EMAIL_DOMAIN}"


def _random_date(start: date, end: date) -> date:
    return start + timedelta(days=rng.randrange((end - start).days + 1))


def _random_time(h_start: int, h_end: int) -> time:
    return time(hour=rng.randrange(h_start, h_end), minute=rng.choice([0, 15, 30, 45]))


# ---------------------------------------------------------------------------
# Tenants
# ---------------------------------------------------------------------------

TENANTS = [
    {
        "key": "retail",
        "name": "BrightMart Retail",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "locale": "en-IN",
        "departments": [
            ("Store Operations", "OPS"),
            ("Sales Floor", "SALES"),
            ("Inventory", "INV"),
            ("Customer Service", "CS"),
            ("Loss Prevention", "LP"),
            ("Warehouse", "WH"),
        ],
        "locations": [
            ("Downtown Store", "DT", "America/New_York"),
            ("North Mall", "NM", "America/New_York"),
            ("West Plaza", "WP", "America/Chicago"),
            ("East Crossing", "EC", "America/Denver"),
        ],
    },
    {
        "key": "construction",
        "name": "SkyLine Construction",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "locale": "en-IN",
        "departments": [
            ("Project Management", "PM"),
            ("Site Operations", "SITE"),
            ("Procurement", "PROC"),
            ("Safety & Compliance", "SAFE"),
            ("Equipment", "EQUIP"),
            ("Finance", "FIN"),
        ],
        "locations": [
            ("Head Office", "HO", "America/Toronto"),
            ("North Tower Site", "NT", "America/Toronto"),
            ("South Bridge Site", "SB", "America/Vancouver"),
            ("East Subdivision", "ES", "America/Halifax"),
        ],
    },
]

ROLE_ACCOUNTS = [
    ("SuperAdmin", "superadmin"),
    # "HR" — the role-constraint migration (0009) limits the role column to
    # the five values the auth layer routes on; "HR Admin" predates it.
    ("HR", "hradmin"),
    ("Manager", "mgr_one"),
    ("Manager", "mgr_two"),
    ("PayrollViewer", "payroll_viewer"),
    ("Associate", "assoc_one"),
    ("Associate", "assoc_two"),
    ("Associate", "assoc_three"),
    ("Associate", "assoc_four"),
    ("Associate", "assoc_five"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_code(db: Session, model, code_value: str, **fields):
    existing = db.query(model).filter(model.code == code_value).first()
    if existing:
        return existing, False
    obj = model(code=code_value, **fields)
    db.add(obj)
    db.flush()
    return obj, True


def _get_or_create_empid(db: Session, model, emp_id: str, **fields):
    existing = db.query(model).filter(model.employee_id == emp_id).first()
    if existing:
        return existing, False
    obj = model(employee_id=emp_id, **fields)
    db.add(obj)
    db.flush()
    return obj, True


def _count(db: Session, table: str) -> int:
    return db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0


# ---------------------------------------------------------------------------
# Seed steps
# ---------------------------------------------------------------------------

def _seed_users(db: Session, prefix: str, creds: list) -> dict:
    users = {}
    for role, username in ROLE_ACCOUNTS:
        uname = f"{prefix}_{username}"
        existing = db.query(User).filter(User.username == uname).first()
        if existing:
            users.setdefault(role, []).append(existing)
            continue
        password = (
            "".join(rng.choice(string.ascii_letters + string.digits) for _ in range(20))
            + "A1!"
        )
        user = User(
            username=uname,
            email=_email(prefix, username, 0, prefix),
            hashed_password=get_password_hash(password),
            role=role,
            is_active=True,
            must_change_password=(role == "SuperAdmin"),
            password_changed_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.flush()
        creds.append(
            {
                "tenant": prefix,
                "role": role,
                "username": uname,
                "password": password,
            }
        )
        users.setdefault(role, []).append(user)
    return users


def _seed_static_data(db: Session, tenant: dict) -> tuple[dict, dict, dict]:
    depts = {}
    for name, code in tenant["departments"]:
        dept, _ = _get_or_create_code(
            db, Department, f"{tenant['key']}-{code}",
            name=name, description=f"{tenant['name']} — {name}", is_active=True,
        )
        depts[name] = dept.id

    locations = {}
    for name, code, tz in tenant["locations"]:
        loc, _ = _get_or_create_code(
            db, Location, f"{tenant['key']}-{code}",
            name=name,
            address=f"{rng.randrange(100, 9999)} Synthetic Street",
            city="Synthetic City",
            country="Test Country",
            timezone=tz,
            is_active=True,
        )
        locations[name] = loc.id

    jobs = {}
    job_specs = [
        ("Store Associate", 28000, 42000),
        ("Senior Associate", 38000, 52000),
        ("Shift Supervisor", 45000, 60000),
        ("Department Manager", 55000, 75000),
        ("Assistant Manager", 50000, 68000),
        ("Project Engineer", 60000, 85000),
        ("Site Foreman", 55000, 78000),
        ("Procurement Officer", 50000, 70000),
        ("Safety Officer", 52000, 72000),
        ("Finance Controller", 58000, 82000),
    ]
    dept_names = list(depts.keys())
    for i, (title, min_s, max_s) in enumerate(job_specs):
        dept_name = dept_names[i % len(dept_names)]
        job, _ = _get_or_create_code(
            db, Job, f"{tenant['key']}-J{i+1:02d}",
            title=title, department_id=depts[dept_name],
            min_salary=min_s, max_salary=max_s, is_active=True,
        )
        jobs[title] = job.id

    return depts, jobs, locations


def _seed_employees(db: Session, prefix: str, depts: dict, jobs: dict,
                    locations: dict, users: dict) -> list:
    dept_ids = list(depts.values())
    job_ids = list(jobs.values())
    loc_ids = list(locations.values())
    employees = []

    senior_count = 12
    for i in range(300):
        idx = i + 1
        first, last = _name().split(" ", 1)
        emp_id = f"{prefix.upper()}-E{idx:04d}"
        hire_date = _random_date(date(2020, 1, 1), date(2026, 10, 1))
        dept_id = rng.choice(dept_ids)
        job_id = rng.choice(job_ids)
        loc_id = rng.choice(loc_ids)

        if i < senior_count:
            manager_id = None
            status = "Active"
        else:
            manager_id = employees[rng.randrange(min(i, senior_count))].id
            status = rng.choice(
                ["Active", "Active", "Active", "On Leave", "Terminated", "Active"]
            )

        salary = round(rng.uniform(30000, 90000), 2)

        emp, _ = _get_or_create_empid(
            db, Employee, emp_id,
            first_name=first, last_name=last,
            email=_email(first, last, idx, prefix),
            phone=f"+1-555-{rng.randrange(100, 999)}-{rng.randrange(1000, 9999)}",
            hire_date=hire_date, job_id=job_id, department_id=dept_id,
            manager_id=manager_id, status=status, salary=salary,
        )
        employees.append(emp)

    # Link one associate user to the first employee
    assoc_users = users.get("Associate", [])
    if assoc_users and employees:
        db.query(User).filter(User.id == assoc_users[0].id).update(
            {"employee_id": employees[0].id}
        )

    return employees


def _seed_leave_data(db: Session, prefix: str, employees: list):
    leave_types = [
        ("Annual Leave", "AL", True, 20),
        ("Sick Leave", "SL", True, 10),
        ("Casual Leave", "CL", True, 5),
        ("Maternity Leave", "ML", True, 90),
        ("Paternity Leave", "PL", True, 14),
        ("Bereavement Leave", "BL", True, 3),
    ]
    for name, code, is_paid, max_days in leave_types:
        _get_or_create_code(
            db, LeaveType, f"{prefix}-{code}",
            name=name, is_paid=is_paid, max_days_per_year=max_days, is_active=True,
        )

    type_map = {
        lt.code: lt.id for lt in db.query(LeaveType).filter(
            LeaveType.code.like(f"{prefix}-%")
        ).all()
    }

    active_emps = [e for e in employees if e.status == "Active"]
    statuses = ["Approved", "Pending", "Rejected", "Cancelled"]
    today = date.today()
    manager_ids = [u.id for u in db.query(User).filter(User.role == "Manager").all()]

    for emp in active_emps:
        for year in (today.year - 1, today.year):
            lt_id = type_map.get(f"{prefix}-AL")
            if lt_id:
                existing = db.query(LeaveBalance).filter(
                    LeaveBalance.employee_id == emp.id,
                    LeaveBalance.leave_type_id == lt_id,
                    LeaveBalance.entitlement_year == year,
                ).first()
                if not existing:
                    db.add(LeaveBalance(
                        employee_id=emp.id, leave_type_id=lt_id,
                        entitlement_year=year,
                        entitled_days=20.0,
                        carried_over_days=5.0,
                        used_days=round(rng.uniform(0, 10), 1),
                    ))
        for _ in range(rng.randrange(1, 4)):
            lt_id = rng.choice(list(type_map.values()))
            start = _random_date(date(today.year - 1, 1, 1), today)
            end = start + timedelta(days=rng.randrange(1, 5))
            status = rng.choice(statuses)
            existing = db.query(LeaveRequest).filter(
                LeaveRequest.employee_id == emp.id,
                LeaveRequest.start_date == start,
                LeaveRequest.end_date == end,
            ).first()
            if not existing:
                lr = LeaveRequest(
                    employee_id=emp.id, leave_type_id=lt_id,
                    start_date=start, end_date=end,
                    working_days=float((end - start).days + 1),
                    reason="Synthetic leave request",
                    status=status,
                )
                db.add(lr)
                db.flush()
                if status in ("Approved", "Rejected") and manager_ids:
                    lr.decided_by = rng.choice(manager_ids)
                    lr.decided_at = datetime.combine(end, time(9, 0), tzinfo=timezone.utc)


def _seed_time_data(db: Session, prefix: str, employees: list):
    TimeEntry = __import__("app.models.time_attendance", fromlist=["TimeEntry"]).TimeEntry
    active_emps = [e for e in employees if e.status == "Active"]
    today = date.today()
    start_date = today - timedelta(weeks=12)

    for emp in active_emps:
        d = start_date
        while d <= today:
            if d.weekday() < 5 and rng.random() < 0.9:
                ci = _random_time(8, 10)
                co = _random_time(17, 19)
                worked = round((co.hour - ci.hour) + (co.minute - ci.minute) / 60, 2)
                ot = max(0.0, worked - 8.0)
                existing = db.query(TimeEntry).filter(
                    TimeEntry.employee_id == emp.id,
                    TimeEntry.work_date == d,
                ).first()
                if not existing:
                    db.add(TimeEntry(
                        employee_id=emp.id, work_date=d,
                        clock_in=datetime.combine(d, ci, tzinfo=timezone.utc),
                        clock_out=datetime.combine(d, co, tzinfo=timezone.utc),
                        break_minutes=30,
                        worked_hours=worked,
                        overtime_hours=round(ot, 2),
                        source="Web",
                        status="Approved",
                    ))
            d += timedelta(days=1)


def main() -> int:
    database_url = _resolve_database_url()
    if _is_production_target(database_url):
        target = database_url.split("@")[-1] if "@" in database_url else database_url
        print(
            f"seed_dev: REFUSING to run against a production/Oracle/remote target ({target})",
            file=sys.stderr,
        )
        return 2

    print(
        f"seed_dev: target database = "
        f"{database_url.split('@')[-1] if '@' in database_url else database_url}"
    )
    if database_url.lower().startswith("oracle+"):
        engine = create_engine(
            "oracle+oracledb://:@",
            pool_pre_ping=True,
            connect_args={
                "user": os.environ["ORACLE_USER"],
                "password": os.environ["ORACLE_PASSWORD"],
                "dsn": os.environ["ORACLE_DSN"],
                "config_dir": os.environ["ORACLE_WALLET_DIR"],
                "wallet_location": os.environ["ORACLE_WALLET_DIR"],
                "wallet_password": os.environ.get("ORACLE_WALLET_PASSWORD", ""),
            },
        )
    else:
        engine = create_engine(database_url)

    import app.models  # noqa: F401

    existing_users = 0
    try:
        with engine.connect() as conn:
            tables = inspect(conn).get_table_names()
            if "users" in tables:
                existing_users = conn.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    except Exception as exc:
        print(f"seed_dev: cannot inspect database: {exc}", file=sys.stderr)
        return 2

    if existing_users > 0:
        if os.environ.get("KARMA_SEED_RESET", "").strip().lower() != "yes":
            print(f"seed_dev: {existing_users} users already present — idempotent, skipping.")
            print("seed_dev: to reseed, set KARMA_SEED_RESET=yes (scratch schemas only).")
            return 0
        print(f"seed_dev: guarded reset — {existing_users} users present; clearing the schema.")
        import app.models  # noqa: F401  (register every model on the metadata)
        Base.metadata.drop_all(bind=engine)
        from app.core.migrations import run_pending_migrations
        state = run_pending_migrations()
        print(f"seed_dev: schema migrated to {state.get('current_revision')}.")

    # The models describe the full head schema; for Oracle the migration
    # runner stamps that as a baseline and applies the later revisions on
    # top — replaying a baseline again would fail its inline ALTERs.
    Base.metadata.create_all(bind=engine)
    from app.core.migrations import run_pending_migrations
    state = run_pending_migrations()
    print(f"seed_dev: schema migrated to {state.get('current_revision')}.")
    db = Session(bind=engine)
    all_employees = []
    creds = []
    try:
        for tenant in TENANTS:
            prefix = tenant["key"]
            users = _seed_users(db, prefix, creds)
            depts, jobs, locations = _seed_static_data(db, tenant)
            emps = _seed_employees(db, prefix, depts, jobs, locations, users)
            all_employees.extend(emps)
            _seed_leave_data(db, prefix, emps)
            _seed_time_data(db, prefix, emps)
        db.commit()

        CREDENTIALS_OUT.write_text(json.dumps(creds, indent=2))
        CREDENTIALS_OUT.chmod(0o600)
        print(f"seed_dev: created {len(creds)} accounts across {len(TENANTS)} tenants.")
        print(f"seed_dev: credentials -> {CREDENTIALS_OUT} (chmod 600, git-ignored).")
        print("seed_dev: done.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
