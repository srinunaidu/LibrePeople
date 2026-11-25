"""Start a local backend for the Playwright suite.

Applies migrations to a throwaway SQLite database, seeds a SuperAdmin and a
few reference records, then serves the API. The database is rebuilt from
scratch on every run so a journey never depends on state left behind by a
previous one.

The bootstrap password comes from ``E2E_ADMIN_PASSWORD`` in the environment.
It is a test fixture, not a deployment secret, and it is only ever used
against a local SQLite file.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

PORT = int(os.environ.get("E2E_PORT", "8010"))
ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "E2e!Bootstrap#2026")
ADMIN_USERNAME = os.environ.get("E2E_ADMIN_USERNAME", "admin")
ADMIN_EMAIL = os.environ.get("E2E_ADMIN_EMAIL", "admin@karmathy.example")

#: A second SuperAdmin that still has to replace its bootstrap password.
#: The forced password-change journey needs its own account: rotating the
#: password on the shared one would make every later sign-in ambiguous.
FIRST_LOGIN_USERNAME = os.environ.get("E2E_FIRST_LOGIN_USERNAME", "firstlogin")
FIRST_LOGIN_PASSWORD = os.environ.get("E2E_FIRST_LOGIN_PASSWORD", "E2e!FirstLogin#2026")
FIRST_LOGIN_EMAIL = "firstlogin@karmathy.example"

#: A third account, also awaiting a password change, for the journey that
#: checks a protected route cannot be reached before the change happens.
#: It is separate because the first-login journey rotates its own account.
PENDING_USERNAME = os.environ.get("E2E_PENDING_USERNAME", "pendingchange")
PENDING_PASSWORD = os.environ.get("E2E_PENDING_PASSWORD", "E2e!Pending#2026")
PENDING_EMAIL = "pendingchange@karmathy.example"

#: A second usable SuperAdmin, for the payroll journey's approval step. The
#: server refuses an approval by the operator who processed the run, so the
#: journey has to act as two people. It keeps a stable password, like the
#: shared account, so the suite is repeatable.
PAY_ADMIN_USERNAME = os.environ.get("E2E_PAY_ADMIN_USERNAME", "payadmin")
PAY_ADMIN_PASSWORD = os.environ.get("E2E_PAY_ADMIN_PASSWORD", "E2e!PayAdmin#2026")
PAY_ADMIN_EMAIL = "payadmin@karmathy.example"

#: The payroll journey calculates a run, and a run is refused unless a
#: `verified` rule pack is in force for its jurisdiction. The directory the
#: product ships holds only a draft demo pack; these are the synthetic fixture
#: packs the backend suites use, labelled "not a statute" in every field. This
#: is a test harness, so it never reaches a deployment.
os.environ.setdefault(
    "RULE_PACK_DIR", str(BACKEND_ROOT / "test_fixtures" / "rule_packs")
)

from app.core.database import SessionLocal  # noqa: E402
from app.core.migrations import run_pending_migrations  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.job_queue import JobQueue, JobState, JobType  # noqa: E402
from app.models.user import User  # noqa: E402


def _reset_database() -> None:
    """Delete the throwaway SQLite file so every run starts clean.

    The journeys rotate passwords and create records. Reusing the file would
    make a later run depend on an earlier one's leftovers.
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("sqlite:///"):
        return
    path = Path(url.replace("sqlite:///", "", 1))
    if path.exists():
        path.unlink()
        print(f"[e2e] removed previous database {path}", flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)


def seed() -> None:
    _reset_database()
    print("[e2e] applying migrations...", flush=True)
    state = run_pending_migrations()
    print(f"[e2e] schema at {state.get('current_revision')}", flush=True)

    db = SessionLocal()
    try:
        # The shared navigation account keeps a stable password so the suite
        # is repeatable: a previous run may have rotated it, recorded failed
        # logins or locked the account.
        admin = db.query(User).filter(User.username == ADMIN_USERNAME).first()
        if admin is None:
            admin = User(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                hashed_password=get_password_hash(ADMIN_PASSWORD),
                role="SuperAdmin",
                is_active=True,
                must_change_password=False,
                mfa_enabled=True,
            )
            db.add(admin)
            print(f"[e2e] created SuperAdmin '{ADMIN_USERNAME}'", flush=True)
        else:
            admin.hashed_password = get_password_hash(ADMIN_PASSWORD)
            admin.must_change_password = False
            admin.failed_login_count = 0
            admin.locked_until = None
            admin.is_active = True
            admin.mfa_enabled = True
            print(f"[e2e] reset SuperAdmin '{ADMIN_USERNAME}'", flush=True)
        db.commit()

        # A second SuperAdmin that must replace its bootstrap password. It
        # exercises the forced password-change journey without disturbing
        # the shared navigation account.
        for username, password, email in (
            (FIRST_LOGIN_USERNAME, FIRST_LOGIN_PASSWORD, FIRST_LOGIN_EMAIL),
            (PENDING_USERNAME, PENDING_PASSWORD, PENDING_EMAIL),
        ): 
            account = db.query(User).filter(User.username == username).first()
            if account is None:
                db.add(
                    User(
                        username=username,
                        email=email,
                        hashed_password=get_password_hash(password),
                        role="SuperAdmin",
                        is_active=True,
                        must_change_password=True,
                        mfa_enabled=True,
                    )
                )
                print(f"[e2e] created SuperAdmin '{username}'", flush=True)
            else:
                account.hashed_password = get_password_hash(password)
                account.must_change_password = True
                account.failed_login_count = 0
                account.locked_until = None
                account.is_active = True
                account.mfa_enabled = True
        db.commit()

        # The second actor for the payroll journey. It is a usable account (no
        # forced password change) because the journey signs in as it to approve
        # a run the shared admin processed.
        pay_admin = (
            db.query(User).filter(User.username == PAY_ADMIN_USERNAME).first()
        )
        if pay_admin is None:
            db.add(
                User(
                    username=PAY_ADMIN_USERNAME,
                    email=PAY_ADMIN_EMAIL,
                    hashed_password=get_password_hash(PAY_ADMIN_PASSWORD),
                    role="SuperAdmin",
                    is_active=True,
                    must_change_password=False,
                    mfa_enabled=True,
                )
            )
            print(f"[e2e] created SuperAdmin '{PAY_ADMIN_USERNAME}'", flush=True)
        else:
            pay_admin.hashed_password = get_password_hash(PAY_ADMIN_PASSWORD)
            pay_admin.role = "SuperAdmin"
            pay_admin.must_change_password = False
            pay_admin.failed_login_count = 0
            pay_admin.locked_until = None
            pay_admin.is_active = True
            pay_admin.mfa_enabled = True
            print(f"[e2e] reset SuperAdmin '{PAY_ADMIN_USERNAME}'", flush=True)
        db.commit()

        if not db.query(Department).filter(Department.code == "OPS").first():
            db.add(
                Department(
                    name="Operations",
                    code="OPS",
                    description="Operations department for end-to-end journeys",
                )
            )
            db.commit()

        ops = db.query(Department).filter(Department.code == "OPS").first()
        if not db.query(Job).filter(Job.code == "OPS-MGR").first():
            db.add(
                Job(
                    title="Operations Manager",
                    code="OPS-MGR",
                    department_id=ops.id,
                    min_salary=0,
                    max_salary=0,
                )
            )
            db.commit()

        # The employee the payroll journey gives a pay profile to. It is a
        # fixture of the harness, not a person: the journeys never depend on a
        # record another journey creates, and a staging schema survives between
        # runs, so the row is reused rather than re-created.
        ops_job = db.query(Job).filter(Job.code == "OPS-MGR").first()

        if not db.query(Employee).filter(Employee.employee_id == "PAY-001").first():
            db.add(
                Employee(
                    employee_id="PAY-001",
                    first_name="Payroll",
                    last_name="Fixture",
                    email="payroll.fixture@example.com",
                    hire_date=date(2024, 1, 2),
                    job_id=ops_job.id,
                    department_id=ops.id,
                    status="Active",
                    employment_type="Full-time",
                )
            )
            db.commit()
            print("[e2e] created the payroll fixture employee", flush=True)

        # Background jobs for the monitor journey (PS-10). The queue writes
        # these in normal operation; the journey needs one of each shape it
        # acts on: a dead import to retry, a waiting import to discard, and a
        # finished forecast to show that the listing is not only failures.
        fixtures = (
            {
                "input_hash": hashlib.sha256(b"e2e-dead-import").hexdigest(),
                "job_type": JobType.CSV_IMPORT.value,
                "state": JobState.DEAD.value,
                "attempts": 3,
                "max_attempts": 3,
                "error_code": "import_row_rejected",
                "error_message": "Row 14: the department code does not exist.",
            },
            {
                "input_hash": hashlib.sha256(b"e2e-pending-import").hexdigest(),
                "job_type": JobType.CSV_IMPORT.value,
                "state": JobState.QUEUED.value,
                "attempts": 0,
                "max_attempts": 5,
            },
            {
                # A finished job with a stored input and a stored result, so
                # the monitor journey can prove the detail read actually
                # serves what the queue kept (`0025_job_result_payload`).
                # The shape is what `roster_solve` returns.
                "input_hash": hashlib.sha256(b"e2e-succeeded-solve").hexdigest(),
                "job_type": JobType.ROSTER_SOLVE.value,
                "state": JobState.SUCCEEDED.value,
                "attempts": 1,
                "max_attempts": 5,
                "input_json": json.dumps(
                    {"time_limit_seconds": 60, "problem": {"slots": 14}},
                    sort_keys=True,
                ),
                "result_json": json.dumps(
                    {
                        "status": "FEASIBLE",
                        "solver_status": "FEASIBLE",
                        "objective_value": 128.5,
                        "assignments": 14,
                        "unfilled": [],
                    },
                    sort_keys=True,
                ),
            },
        )
        for fixture in fixtures:
            row = (
                db.query(JobQueue)
                .filter(JobQueue.input_hash == fixture["input_hash"])
                .first()
            )
            if row is None:
                db.add(
                    JobQueue(
                        **fixture,
                        last_error_at=(
                            datetime.now(timezone.utc)
                            if fixture.get("error_code")
                            else None
                        ),
                    )
                )
                continue
            # These rows are not immutable fixtures: the monitor journey
            # retries the dead one and discards the waiting one. Skipping an
            # existing row therefore left the second run of the gate with no
            # dead job at all, and the journey failed on a state the first run
            # had created (D-037). Reset it to the state the journey expects.
            row.job_type = fixture["job_type"]
            row.state = fixture["state"]
            row.attempts = fixture["attempts"]
            row.max_attempts = fixture["max_attempts"]
            row.error_code = fixture.get("error_code")
            row.error_message = fixture.get("error_message")
            row.worker_id = None
            row.lease_expires_at = None
            row.started_at = None
            row.finished_at = None
            row.result_hash = None
            # The fixtures carry their own stored input and result; a row
            # without them must be reset to none, not left holding the
            # previous run's value.
            row.input_json = fixture.get("input_json")
            row.result_json = fixture.get("result_json")
            row.last_error_at = (
                datetime.now(timezone.utc)
                if fixture.get("error_code")
                else None
            )
            db.add(row)
        db.commit()
        print("[e2e] background jobs ready", flush=True)
        print("[e2e] reference records ready", flush=True)
    finally:
        db.close()


def main() -> None:
    seed()
    import uvicorn

    from app.main import app

    print(f"[e2e] serving on http://127.0.0.1:{PORT}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
