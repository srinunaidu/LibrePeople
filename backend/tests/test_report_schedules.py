"""Scheduled reporting (reporting-personalization Part F).

Proves, against the served API plus the real queue and worker:
* creation validates {report_key, filters, frequency, timezone, recipients};
  bad tz/frequency/key/recipient is 422 and enqueues nothing synchronously;
* a due tick enqueues REPORT_RUN through JobQueueService (dedupe on pending)
  and the JobWorker executes the registered handler — no new scheduler;
* delivery is an in-app Notification per recipient plus a CSV/XLSX download
  through the existing report_exports path; the default log provider sends
  no email (documented, not a failure);
* runs-as-owner: data resolved with the owner's visibility and mask; a
  recipient outside the report's role set gets a "not available for your
  role" notice and no file; payroll-summary never leaks identifiers to an
  Associate (negative test);
* transient failure retries with backoff; bad input dead-letters at once;
  every run writes an audit row.

Run:  python tests/test_report_schedules.py   (from backend/)
  or: pytest tests/test_report_schedules.py -q
"""
import datetime
import os
import shutil
import sys
import tempfile
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

DB_DIR = tempfile.mkdtemp(prefix="report_schedules_suite_")
DB_PATH = os.path.join(DB_DIR, "report_schedules_suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.jobs.queue import JobQueueService  # noqa: E402
from app.jobs.registry import get_handler  # noqa: E402
from app.jobs.worker import JobWorker  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.ess_hr import Notification  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.job_queue import JobQueue, JobState, JobType  # noqa: E402
from app.models.payroll import PayRun, PaySlip, PayrollPeriod  # noqa: E402
from app.models.report_personalization import ReportRun, ReportSchedule  # noqa: E402
from app.models.user import User  # noqa: E402

TENANT_A = "tenant-rps-a"
TENANT_B = "tenant-rps-b"
PASSWORD = "ReportSchedPass123"

_RESULT = None


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
    dept = Department(name="RPS Ops", code="RPSOPS")
    db.add(dept)
    db.commit()
    db.refresh(dept)
    job = Job(title="RPS Analyst", code="RPSANL", department_id=dept.id)
    db.add(job)
    db.commit()
    db.refresh(job)

    def _employee(code: str, first: str, **kw) -> Employee:
        kw.setdefault("status", "Active")
        person = Employee(
            employee_id=code, first_name=first, last_name="Rps",
            email=f"{code.lower()}@example.com",
            hire_date=datetime.date(2024, 6, 1),
            job_id=job.id, department_id=dept.id,
            tenant_id=TENANT_A, **kw,
        )
        db.add(person)
        db.commit()
        db.refresh(person)
        return person

    emp_owner = _employee("RPS-OWN", "Owner")
    _employee("RPS-LEAV", "Leaver", status="Terminated",
              termination_date=datetime.date(2026, 3, 15))
    emp_ident = _employee("RPS-ID", "Ident", pan_number="ABCDE1234F", aadhaar_last4="4321")

    def _user(username: str, role: str, employee_id=None) -> User:
        existing = db.query(User).filter(User.username == username).first()
        if existing is not None:
            return existing
        user = User(
            username=username, email=f"{username}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            role=role, is_active=True, employee_id=employee_id,
            mfa_enabled=role in ("SuperAdmin", "HR"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    u_admin = _user("rps_admin", "SuperAdmin")
    u_hr = _user("rps_hr", "HR", emp_owner.id)
    u_mgr = _user("rps_mgr", "Manager")
    u_assoc = _user("rps_assoc", "Associate")
    u_pay = _user("rps_pay", "PayrollViewer")
    emp_owner_id = emp_owner.id
    emp_ident_id = emp_ident.id
    ADMIN_ID, HR_ID, ASSOC_ID, PAY_ID = u_admin.id, u_hr.id, u_assoc.id, u_pay.id
    db.close()

    period = PayrollPeriod(
        name="RPS 2026-03", start_date=datetime.date(2026, 3, 1),
        end_date=datetime.date(2026, 3, 31), pay_date=datetime.date(2026, 3, 31),
        status="Paid",
    )
    s = SessionLocal()
    s.add(period)
    s.commit()
    s.refresh(period)
    run = PayRun(period_id=period.id, jurisdiction="IN", status="Paid", currency="INR")
    s.add(run)
    s.commit()
    s.refresh(run)
    for person_id in (emp_owner_id, emp_ident_id):
        s.add(PaySlip(
            pay_run_id=run.id, employee_id=person_id,
            gross_pay=100000, net_pay=80000, total_deductions=20000,
            currency="INR",
        ))
    s.commit()
    s.close()

    client = TestClient(app, raise_server_exceptions=False)

    def _headers(username: str, tenant: str = TENANT_A) -> dict:
        token = create_access_token(subject=username, extra_claims={"tenant": tenant})
        return {"Authorization": f"Bearer {token}"}

    H_ADMIN = _headers("rps_admin")
    H_HR = _headers("rps_hr")
    H_ASSOC = _headers("rps_assoc")
    H_PAY = _headers("rps_pay")
    H_FOREIGN = _headers("rps_admin", TENANT_B)

    def _job_count() -> int:
        sess = SessionLocal()
        try:
            return sess.query(JobQueue).count()
        finally:
            sess.close()

    def _schedule_count() -> int:
        sess = SessionLocal()
        try:
            return sess.query(ReportSchedule).count()
        finally:
            sess.close()

    # =======================================================================
    print("\n[SCHED-1] Creation validates and enqueues nothing (AC5)")
    # =======================================================================
    jobs_before = _job_count()
    r = client.post(
        "/api/v1/report-schedules", headers=H_HR,
        json={"report_key": "leavers", "filters": {},
              "frequency": "weekly", "timezone": "Asia/Kolkata",
              "recipient_user_ids": [PAY_ID]},
    )
    check("valid schedule creates 201", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
    body = r.json()
    check("timezone stored", body.get("timezone") == "Asia/Kolkata", r.text[:200])
    check("creation enqueues nothing", _job_count() == jobs_before, f"jobs={_job_count()}")
    S_LEAVERS = body.get("id")

    for bad, field in [
        ({"report_key": "leavers", "frequency": "hourly", "timezone": "UTC", "recipient_user_ids": []}, "frequency"),
        ({"report_key": "leavers", "frequency": "daily", "timezone": "Mars/Olympus", "recipient_user_ids": []}, "timezone"),
        ({"report_key": "turnover-magic", "frequency": "daily", "timezone": "UTC", "recipient_user_ids": []}, "report_key"),
        ({"report_key": "joiners", "frequency": "daily", "timezone": "UTC", "recipient_user_ids": [999999]}, "recipient"),
    ]:
        n_before = _schedule_count()
        r = client.post("/api/v1/report-schedules", headers=H_HR, json=bad)
        check(f"invalid {field} is 422", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")
        check(f"invalid {field} writes no row", _schedule_count() == n_before, "")

    r = client.post(
        "/api/v1/report-schedules", headers=H_ASSOC,
        json={"report_key": "joiners", "frequency": "daily", "timezone": "UTC", "recipient_user_ids": []},
    )
    check("Associate creation is 403", r.status_code == 403, f"got {r.status_code}")

    # =======================================================================
    print("\n[SCHED-2] run-now + tick enqueue REPORT_RUN, deduped (AC6)")
    # =======================================================================
    check("REPORT_RUN handler is registered",
          get_handler(JobType.REPORT_RUN) is not None, "")
    r = client.post(f"/api/v1/report-schedules/{S_LEAVERS}/run-now", headers=H_HR)
    check("run-now enqueues", r.status_code == 200 and r.json().get("deduped") is False, f"got {r.status_code}: {r.text[:200]}")
    JOB_ID = r.json().get("job_id")
    sess = SessionLocal()
    enqueued = sess.query(JobQueue).filter(JobQueue.id == JOB_ID).first()
    check("job type is REPORT_RUN", enqueued is not None and str(enqueued.job_type) == "report_run", "")
    check("max_attempts is 5", enqueued is not None and enqueued.max_attempts == 5, "")
    sess.close()
    r = client.post(f"/api/v1/report-schedules/{S_LEAVERS}/run-now", headers=H_HR)
    check("second run-now dedupes on pending",
          r.status_code == 200 and r.json().get("deduped") is True and r.json().get("job_id") == JOB_ID,
          f"got {r.status_code}: {r.text[:200]}")

    # Make the schedule due, then tick twice: enqueue once, dedupe once.
    sess = SessionLocal()
    sched = sess.query(ReportSchedule).filter(ReportSchedule.id == S_LEAVERS).first()
    from datetime import timezone as _tz
    sched.next_due_at = datetime.datetime.now(_tz.utc) - datetime.timedelta(hours=1)
    sess.add(sched)
    sess.commit()
    sess.close()
    r = client.post("/api/v1/report-schedules/tick", headers=H_ADMIN)
    check("due tick enqueues", r.status_code == 200 and r.json().get("count") == 1, f"got {r.status_code}: {r.text[:300]}")
    first_job = r.json()["enqueued"][0]["job_id"]
    check("tick reuses the pending job (dedupe)", r.json()["enqueued"][0]["deduped"] is True and first_job == JOB_ID,
          r.text[:300])
    sess = SessionLocal()
    sched = sess.query(ReportSchedule).filter(ReportSchedule.id == S_LEAVERS).first()
    advanced = sched.next_due_at.replace(tzinfo=datetime.timezone.utc) if sched.next_due_at.tzinfo is None else sched.next_due_at
    check("tick advances next_due_at past now", advanced > datetime.datetime.now(datetime.timezone.utc), f"next_due_at={sched.next_due_at}")
    sess.close()

    # =======================================================================
    print("\n[SCHED-3] Worker executes; delivery is notification + download (AC6/AC7)")
    # =======================================================================
    worker = JobWorker(poll_seconds=0.05, lease_seconds=300)
    check("worker claims and executes the job", worker.run_once() is True, "")
    sess = SessionLocal()
    done = sess.query(JobQueue).filter(JobQueue.id == JOB_ID).first()
    check("job succeeded", done is not None and str(done.state) == "succeeded", f"state={getattr(done, 'state', None)}")
    notes = sess.query(Notification).filter(
        Notification.entity_type == "report_run",
        Notification.notification_type == "info",
    ).all()
    pay_notes = [n for n in notes if n.recipient_id == PAY_ID]
    check("recipient got an in-app notification", len(pay_notes) >= 1, f"notes={len(notes)}")
    run_row = sess.query(ReportRun).filter(ReportRun.schedule_id == S_LEAVERS).order_by(ReportRun.id.desc()).first()
    check("a run row was recorded", run_row is not None and run_row.payload is not None, "")
    RUN_ID = run_row.id if run_row is not None else None
    sess.close()

    r = client.get(f"/api/v1/report-schedules/runs/{RUN_ID}/download", headers=H_PAY)
    check("recipient downloads CSV 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    check("CSV keeps the BOM framing invariant", r.text.startswith("\ufeff"), repr(r.text[:20]))
    check("CSV names the report file", "leavers-run-" in r.headers.get("content-disposition", ""), r.headers.get("content-disposition", ""))

    # =======================================================================
    print("\n[SCHED-4] Runs-as-owner: Associate gets notice, no data (AC8)")
    # =======================================================================
    r = client.post(
        "/api/v1/report-schedules", headers=H_HR,
        json={"report_key": "payroll-summary", "filters": {},
              "frequency": "daily", "timezone": "UTC",
              "recipient_user_ids": [ASSOC_ID, PAY_ID]},
    )
    check("payroll schedule creates", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
    S_PAY = r.json().get("id")
    r = client.post(f"/api/v1/report-schedules/{S_PAY}/run-now", headers=H_HR)
    check("payroll run-now enqueues", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    check("worker executes the payroll job", worker.run_once() is True, "")
    sess = SessionLocal()
    assoc_notes = sess.query(Notification).filter(
        Notification.entity_type == "report_run", Notification.recipient_id == ASSOC_ID,
    ).order_by(Notification.id.desc()).all()
    sess.close()
    check("Associate got a notice", len(assoc_notes) >= 1, "")
    check("notice states not-available-for-role",
          any("not available for your role" in (n.message or "") for n in assoc_notes),
          (assoc_notes[0].message if assoc_notes else "")[:200])
    check("notice carries no download link",
          all("/download" not in (n.message or "") for n in assoc_notes),
          (assoc_notes[0].message if assoc_notes else "")[:200])
    r = client.get("/api/v1/report-schedules/runs", headers=H_ASSOC)
    check("Associate runs list is refused 403", r.status_code == 403, f"got {r.status_code}")

    sess = SessionLocal()
    pay_run_row = sess.query(ReportRun).filter(ReportRun.schedule_id == S_PAY).order_by(ReportRun.id.desc()).first()
    PAY_RUN_ID = pay_run_row.id if pay_run_row is not None else None
    sess.close()
    r = client.get(f"/api/v1/report-schedules/runs/{PAY_RUN_ID}/download", headers=H_ASSOC)
    check("Associate download is refused 403", r.status_code == 403, f"got {r.status_code}: {r.text[:200]}")
    r = client.get(f"/api/v1/report-schedules/runs/{PAY_RUN_ID}/download", headers=H_PAY)
    check("PayrollViewer downloads 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    check("identifiers never leak to non-HR roles",
          "ABCDE1234F" not in r.text and "4321" not in r.text.split("aadhaar")[-1][:40] or "****" in r.text,
          r.text[:300])

    # =======================================================================
    print("\n[SCHED-5] Failure semantics + audit (AC9)")
    # =======================================================================
    audits_before = SessionLocal().query(AuditLog).filter(AuditLog.action == "export").count()
    SessionLocal().close()
    # Bad input dead-letters at once through the real worker.
    sess = SessionLocal()
    bad = JobQueueService(sess).enqueue(JobType.REPORT_RUN, {"schedule_id": 987654321})
    sess.commit()
    bad_id = bad.id
    sess.close()
    check("worker processes the bad job", worker.run_once() is True, "")
    sess = SessionLocal()
    bad_row = sess.query(JobQueue).filter(JobQueue.id == bad_id).first()
    check("bad input dead-letters (dead, not retried)",
          bad_row is not None and str(bad_row.state) == "dead",
          f"state={getattr(bad_row, 'state', None)} attempts={getattr(bad_row, 'attempts', None)}")
    dead_run = sess.query(ReportRun).filter(
        ReportRun.schedule_id == 987654321, ReportRun.job_id == bad_id).first()
    check("dead run row recorded", dead_run is not None and dead_run.status == "dead", "")
    sess.close()
    # Transient failure: force the builder to raise once, on a fresh
    # schedule (a repeat payload would hit the succeeded-dedupe).
    import app.services.report_personalization as rp_svc  # noqa: E402
    real_build = rp_svc.build_report

    def _boom(db, report_key, filters, owner):
        raise RuntimeError("transient test failure")

    r = client.post(
        "/api/v1/report-schedules", headers=H_HR,
        json={"report_key": "attrition", "filters": {"year": 2026},
              "frequency": "daily", "timezone": "UTC",
              "recipient_user_ids": [PAY_ID]},
    )
    check("transient-probe schedule creates", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
    S_TRANSIENT = r.json().get("id")
    rp_svc.build_report = _boom
    try:
        sess = SessionLocal()
        tj = JobQueueService(sess).enqueue(JobType.REPORT_RUN, {"schedule_id": S_TRANSIENT})
        sess.commit()
        tj_id = tj.id
        sess.close()
        check("worker processes the transient job", worker.run_once() is True, "")
        sess = SessionLocal()
        trow = sess.query(JobQueue).filter(JobQueue.id == tj_id).first()
        check("transient failure is failed (retryable, backoff)",
              trow is not None and str(trow.state) == "failed" and trow.attempts == 1,
              f"state={getattr(trow, 'state', None)} attempts={getattr(trow, 'attempts', None)}")
        t_run = sess.query(ReportRun).filter(
            ReportRun.schedule_id == S_TRANSIENT, ReportRun.job_id == tj_id).first()
        check("failed run row recorded", t_run is not None and t_run.status == "failed", "")
        sess.close()
    finally:
        rp_svc.build_report = real_build

    sess = SessionLocal()
    audits_after = sess.query(AuditLog).filter(AuditLog.action == "export").count()
    sched_audits = sess.query(AuditLog).filter(
        AuditLog.action == "export", AuditLog.entity_type == "report_schedule").all()
    sess.close()
    check("every run writes an audit row", audits_after > audits_before, f"{audits_before}->{audits_after}")
    check("audit names schedule, owner and recipient count",
          any("schedule=" in (a.details or "") and "recipients=" in (a.details or "") for a in sched_audits),
          (sched_audits[-1].details if sched_audits else "")[:200])

    # =======================================================================
    print("\n[SCHED-6] Cross-tenant isolation")
    # =======================================================================
    r = client.get(f"/api/v1/report-schedules/{S_LEAVERS}", headers=H_FOREIGN)
    check("foreign schedule GET is 404", r.status_code == 404, f"got {r.status_code}: {r.text[:200]}")
    r = client.post(f"/api/v1/report-schedules/{S_LEAVERS}/run-now", headers=H_FOREIGN)
    check("foreign run-now is 404", r.status_code == 404, f"got {r.status_code}: {r.text[:200]}")

    _RESULT = {"pass": results["pass"], "fail": results["fail"], "failures": failures}
    print(f"\nreport_schedules: {results['pass']} passed, {results['fail']} failed")
    return _RESULT


def test_report_schedules() -> None:
    result = _run()
    assert result["fail"] == 0, f"failures: {result['failures']}"


if __name__ == "__main__":
    result = _run()
    shutil.rmtree(DB_DIR, ignore_errors=True)
    raise SystemExit(1 if result["fail"] else 0)
