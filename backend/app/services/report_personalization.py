"""Saved views and scheduled reporting over the existing read-only reports.

Part E persists named filter sets; Part F executes schedules through the
existing job queue as ``REPORT_RUN`` jobs, runs-as-owner, and delivers an
in-app notification per recipient with a download rendered through the
existing ``report_exports`` path.

This module holds the shared rules (allowlist, validation, role sets, due
arithmetic, report building, schedule execution) so the HTTP layer and the
job handler cannot drift apart. It changes no existing report calculation,
masking, or CSV/XLSX bytes: movement reports go through
:mod:`app.crud.crud_reports` and every row through
:mod:`app.services.report_exports` masking, exactly like the synchronous
endpoints in ``reports.py``.
"""
from __future__ import annotations

import base64
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.core.booleans import is_true
from app.core.visibility import resolve_visible_employee_ids

#: Report keys a view or schedule may name. Nothing else validates.
REPORT_KEYS = ("joiners", "leavers", "attrition", "payroll-summary")

#: Which roles may receive each report. Movement reports are a team view as
#: well as an HR view (mirrors ``WORKFORCE_REPORT_ROLES`` in reports.py);
#: payroll-summary is HR/payroll only (mirrors ``REPORTS_ROLES``).
REPORT_ROLE_SETS: dict[str, tuple[str, ...]] = {
    "joiners": ("SuperAdmin", "HR", "Manager", "PayrollViewer"),
    "leavers": ("SuperAdmin", "HR", "Manager", "PayrollViewer"),
    "attrition": ("SuperAdmin", "HR", "Manager", "PayrollViewer"),
    "payroll-summary": ("SuperAdmin", "HR", "PayrollViewer"),
}

FREQUENCIES = ("daily", "weekly", "monthly")
OUTPUT_FORMATS = ("csv", "xlsx")
VISIBILITIES = ("personal", "shared")

#: Publishing a view to a role is an HR/SuperAdmin act. A Manager or
#: Associate publish attempt is refused 403 (Managers and Associates are
#: already outside REPORTS_ROLES at the route gate; this covers the
#: PayrollViewer case).
SHARE_ROLES = ("SuperAdmin", "HR")

#: Advance applied when a schedule becomes due, per frequency.
FREQUENCY_DELTA = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": timedelta(days=30),
}


class ReportPersonalizationError(ValueError):
    """A 422-class input refusal: unknown key, bad tz, bad frequency."""


def validate_report_key(report_key: Any) -> str:
    if report_key not in REPORT_KEYS:
        raise ReportPersonalizationError(
            f"report_key must be one of {', '.join(REPORT_KEYS)}"
        )
    return report_key


def validate_visibility(visibility: Any) -> str:
    if visibility not in VISIBILITIES:
        raise ReportPersonalizationError(
            f"visibility must be one of {', '.join(VISIBILITIES)}"
        )
    return visibility


def validate_frequency(frequency: Any) -> str:
    if frequency not in FREQUENCIES:
        raise ReportPersonalizationError(
            f"frequency must be one of {', '.join(FREQUENCIES)}"
        )
    return frequency


def validate_output_format(output_format: Any) -> str:
    if output_format not in OUTPUT_FORMATS:
        raise ReportPersonalizationError(
            f"output_format must be one of {', '.join(OUTPUT_FORMATS)}"
        )
    return output_format


def validate_timezone(name: Any) -> str:
    """An IANA timezone name, else a 422-class refusal."""
    if not isinstance(name, str) or not name.strip():
        raise ReportPersonalizationError("timezone must be a valid IANA name")
    try:
        ZoneInfo(name.strip())
    except (ZoneInfoNotFoundError, ValueError):
        raise ReportPersonalizationError(
            f"timezone must be a valid IANA name, got {name!r}"
        )
    return name.strip()


def default_timezone() -> str:
    """The schedule default when the caller names no timezone.

    D1 resolves the default to the tenant timezone. The product holds no
    tenant-timezone setting (there is no such column or preset), so the
    default is UTC until one exists; any IANA name the caller passes is
    stored and used instead.
    """
    return "UTC"


def compute_next_due(frequency: str, tz_name: str, now: datetime | None = None) -> datetime:
    """The next due instant after ``now`` for ``frequency``."""
    now = now or datetime.now(timezone.utc)
    return now + FREQUENCY_DELTA[validate_frequency(frequency)]


def parse_filters(raw: Any) -> dict:
    """Stored filters as a dict; accepts a dict, a JSON object string, or null."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw) if raw.strip() else {}
        except ValueError:
            raise ReportPersonalizationError("filters must be a JSON object")
        if not isinstance(parsed, dict):
            raise ReportPersonalizationError("filters must be a JSON object")
        return parsed
    raise ReportPersonalizationError("filters must be a JSON object")


def role_may_view_report(role: str | None, report_key: str) -> bool:
    """True when ``role`` is in the report's viewer set (D2 role-targeting)."""
    return role in REPORT_ROLE_SETS.get(report_key, ())


def _parse_day(value: Any, name: str):
    if value is None or value == "":
        return None
    from datetime import date as _date

    try:
        return _date.fromisoformat(str(value).strip())
    except (ValueError, AttributeError):
        raise ReportPersonalizationError(f"{name} must be YYYY-MM-DD")


def build_report(
    db: Session, report_key: str, filters: dict, owner
) -> tuple[list[dict], list[str]]:
    """Build ``(rows, columns)`` for ``report_key`` as ``owner`` would see it.

    Visibility is the owner's (:func:`resolve_visible_employee_ids`) and the
    mask is the owner's role — runs-as-owner scoping for scheduled delivery.
    The synchronous ``reports.py`` endpoints are untouched; this mirrors
    their read path (same crud calls, same export masking and columns).
    """
    from app.crud import crud_reports as crud
    from app.services import report_exports as exports

    validate_report_key(report_key)
    filters = dict(filters or {})
    visible_ids = resolve_visible_employee_ids(db, owner)

    if report_key in ("joiners", "leavers"):
        start = _parse_day(filters.get("from"), "from") or date(date.today().year, 1, 1)
        end = _parse_day(filters.get("to"), "to") or date.today()
        if start > end:
            raise ReportPersonalizationError("from must be on or before to")
        scope = dict(
            from_date=start,
            to_date=end,
            entity_id=filters.get("entity_id"),
            department_id=filters.get("department_id"),
            location_id=filters.get("location_id"),
            visible_ids=visible_ids,
        )
        if report_key == "joiners":
            rows = crud.joiners_report(db, **scope)
            columns = [
                "employee_id", "first_name", "last_name", "email",
                "hire_date", "termination_date", "status",
                "department", "legal_entity",
            ]
        else:
            rows = crud.leavers_report(db, **scope)
            columns = [
                "employee_id", "first_name", "last_name", "email",
                "hire_date", "termination_date", "status",
                "department", "legal_entity",
            ]
        return [exports.mask_movement_row(r, owner.role) for r in rows], columns

    if report_key == "attrition":
        year = filters.get("year") or date.today().year
        try:
            year = int(year)
        except (TypeError, ValueError):
            raise ReportPersonalizationError("year must be between 1900 and 2100")
        if year < 1900 or year > 2100:
            raise ReportPersonalizationError("year must be between 1900 and 2100")
        result = crud.attrition_report(
            db,
            year=year,
            entity_id=filters.get("entity_id"),
            department_id=filters.get("department_id"),
            location_id=filters.get("location_id"),
            visible_ids=visible_ids,
        )
        rows = [{**result["filters"], **{k: v for k, v in result.items() if k != "filters"}}]
        columns = [
            "year", "joiners", "leavers", "headcount_start",
            "headcount_end", "average_headcount", "attrition_pct",
        ]
        return rows, columns

    # payroll-summary: stored payslip totals in a date range, read-only.
    # Mirrors the /reports/payroll-summary endpoint's read path (no engine
    # import, per-role identifier masking), scoped by the caller's filters.
    from app.models.employee import Employee
    from app.models.payroll import PayRun, PaySlip

    start = _parse_day(filters.get("from"), "from")
    end = _parse_day(filters.get("to"), "to")
    if start and end and start > end:
        raise ReportPersonalizationError("from must be on or before to")
    q = (
        db.query(PaySlip, PayRun, Employee)
        .join(PayRun, PaySlip.pay_run_id == PayRun.id)
        .join(Employee, PaySlip.employee_id == Employee.id)
        .order_by(PaySlip.id.asc())
    )
    if filters.get("entity_id") is not None:
        q = q.filter(Employee.legal_entity_id == filters.get("entity_id"))
    if filters.get("department_id") is not None:
        q = q.filter(Employee.department_id == filters.get("department_id"))

    def _run_day(run) -> Any:
        period = getattr(run, "period", None)
        return getattr(period, "pay_date", None) if period is not None else None

    rows: list[dict] = []
    for slip, run, emp in q.all():
        day = _run_day(run)
        if start and (day is None or day < start):
            continue
        if end and (day is None or day > end):
            continue
        if visible_ids is not None and emp.id not in visible_ids:
            continue
        pan = getattr(emp, "pan_number", None)
        if pan and isinstance(pan, str) and pan.startswith("ENCv1:"):
            try:
                from app.core.encryption import decrypt_field

                pan = decrypt_field(pan)
            except Exception:
                pass
        aadhaar = getattr(emp, "aadhaar_masked", None) or (
            f"****-****-{emp.aadhaar_last4}" if getattr(emp, "aadhaar_last4", None) else None
        )
        rows.append(
            exports.mask_payroll_row(
                {
                    "payslip_id": slip.id,
                    "pay_run_id": slip.pay_run_id,
                    "employee_id": emp.employee_id,
                    "employee_name": f"{emp.first_name} {emp.last_name}",
                    "gross": str(slip.gross_pay),
                    "net": str(slip.net_pay),
                    "total_deductions": str(slip.total_deductions),
                    "employee_contributions": str(slip.employee_contributions)
                    if slip.employee_contributions is not None
                    else None,
                    "employer_contributions": str(slip.employer_contributions)
                    if slip.employer_contributions is not None
                    else None,
                    "currency": slip.currency,
                    "pan_number": pan,
                    "aadhaar_number": aadhaar,
                },
                owner.role,
            )
        )
    columns = [
        "payslip_id", "pay_run_id", "employee_id", "employee_name",
        "gross", "net", "total_deductions", "employee_contributions",
        "employer_contributions", "currency", "pan_number", "aadhaar",
    ]
    return rows, columns


def render_payload(rows: list[dict], columns: list[str], output_format: str) -> tuple[str, str]:
    """Render rows through the existing export path.

    Returns ``(payload, format)`` where the payload is CSV text or base64
    xlsx, suitable for storing on the run row.
    """
    from app.services import report_exports as exports

    fmt = validate_output_format(output_format)
    if fmt == "csv":
        return exports.rows_to_csv(rows, columns), "csv"
    raw = exports.rows_to_xlsx(rows, columns)
    return base64.b64encode(raw).decode("ascii"), "xlsx"


def enqueue_schedule_job(db: Session, schedule_id: int):
    """Enqueue a REPORT_RUN for ``schedule_id``, deduped on pending work.

    Returns ``(job, deduped)``: when a queued or running job with the same
    payload already exists it is reused instead of enqueuing a duplicate.
    """
    from app.jobs.queue import JobQueueService, compute_input_hash
    from app.models.job_queue import JobQueue, JobState, JobType

    payload = {"schedule_id": schedule_id}
    input_hash = compute_input_hash(payload)
    pending = (
        db.query(JobQueue)
        .filter(
            JobQueue.job_type == JobType.REPORT_RUN,
            JobQueue.input_hash == input_hash,
            JobQueue.state.in_([JobState.QUEUED, JobState.RUNNING]),
        )
        .order_by(JobQueue.id.asc())
        .first()
    )
    if pending is not None:
        return pending, True
    job = JobQueueService(db).enqueue(JobType.REPORT_RUN, payload)
    return job, False


def enqueue_due_schedules(db: Session, now: datetime | None = None) -> list[dict]:
    """Enqueue every active schedule whose due instant has passed.

    Each enqueue reuses :func:`enqueue_schedule_job` (dedupe on pending)
    and advances the schedule's ``next_due_at`` past ``now``, so a tick
    never double-fires a schedule. No new scheduler or cron process: the
    tick is an explicit admin trigger; the queue and the JobWorker do the
    rest.
    """
    from app.models.report_personalization import ReportSchedule

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    def _as_aware(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    # Due filtering happens in Python, not in SQL: SQLite returns naive
    # datetimes for timezone-aware columns while Postgres returns aware
    # ones, so a SQL ``<=`` against an aware parameter is dialect-fragile.
    candidates = (
        db.query(ReportSchedule)
        .filter(is_true(ReportSchedule.active))
        .order_by(ReportSchedule.id.asc())
        .all()
    )
    due = [
        s for s in candidates
        if _as_aware(s.next_due_at) is None or _as_aware(s.next_due_at) <= now
    ]
    outcomes: list[dict] = []
    for schedule in due:
        job, deduped = enqueue_schedule_job(db, schedule.id)
        base = _as_aware(schedule.next_due_at) or now
        while base <= now:
            base = compute_next_due(
                schedule.frequency, schedule.timezone or "UTC", base
            )
        schedule.next_due_at = base
        db.add(schedule)
        outcomes.append(
            {"schedule_id": schedule.id, "job_id": job.id, "deduped": deduped}
        )
    db.commit()
    return outcomes


def execute_report_schedule(db: Session, schedule, job) -> dict:
    """Run one schedule delivery, runs-as-owner. The REPORT_RUN core.

    * Resolves data with the *owner's* visibility and the *owner's* role
      mask — never the recipient's.
    * A recipient whose role is outside the report's role set gets an
      in-app notice stating the report is not available for their role,
      and no file.
    * Email goes out only when ``EMAIL_PROVIDER=smtp``; the default log
      provider means in-app only, which is documented and not a failure.
    * Bad input (missing schedule, unknown stored key) raises
      ``JobInputInvalid`` so the worker dead-letters at once; anything
      else propagates as a transient failure for retry with backoff.
    * Every execution writes an audit row (action ``export``, the schedule
      id, the owner, the recipient count).
    """
    import json as _json

    from app.jobs.errors import JobInputInvalid
    from app.models.ess_hr import Notification
    from app.models.user import User

    if schedule is None:
        raise JobInputInvalid("a report run needs an existing schedule")

    owner = None
    recipient_ids: list = []
    try:
        validate_report_key(schedule.report_key)
        filters = parse_filters(schedule.filters_json)
        recipient_ids = _json.loads(schedule.recipient_ids_json or "[]")
        if not isinstance(recipient_ids, list):
            raise ValueError("recipient ids must be a list")
        owner = db.query(User).filter(User.id == schedule.owner_id).first()
        if owner is None:
            raise JobInputInvalid("schedule owner no longer exists")
        rows, columns = build_report(db, schedule.report_key, filters, owner)
    except JobInputInvalid as exc:
        _record_run(db, schedule.id, job, status="dead", error=str(exc))
        _audit_run(db, owner, schedule.id, schedule.report_key, len(recipient_ids), 0, "dead")
        raise
    except (ReportPersonalizationError, ValueError) as exc:
        _record_run(db, schedule.id, job, status="dead", error=str(exc))
        _audit_run(db, owner, schedule.id, schedule.report_key, len(recipient_ids), 0, "dead")
        raise JobInputInvalid(str(exc)) from None
    except Exception as exc:  # noqa: BLE001 — transient: retry with backoff
        _record_run(
            db, schedule.id, job, status="failed",
            recipient_count=len(recipient_ids),
            error=f"{type(exc).__name__}: {exc}",
        )
        _audit_run(db, owner, schedule.id, schedule.report_key, len(recipient_ids), 0, "failed")
        raise

    payload, fmt = render_payload(rows, columns, schedule.output_format or "csv")
    run = _record_run(
        db, schedule.id, job, status="delivered", payload=payload,
        payload_format=fmt, recipient_count=len(recipient_ids),
    )
    download = f"/api/v1/report-schedules/runs/{run.id}/download"

    delivered = 0
    for recipient_id in recipient_ids:
        recipient = db.query(User).filter(User.id == int(recipient_id)).first()
        if recipient is None:
            continue
        if role_may_view_report(recipient.role, schedule.report_key):
            message = (
                f"Scheduled report '{schedule.report_key}' is ready "
                f"({len(rows)} rows). Download: {download}"
            )
            delivered += 1
        else:
            message = (
                f"Scheduled report '{schedule.report_key}' is not available "
                f"for your role. No file was attached."
            )
        db.add(
            Notification(
                recipient_id=recipient.id,
                title=f"Scheduled report: {schedule.report_key}",
                message=message,
                notification_type="info",
                category="system",
                entity_type="report_run",
                entity_id=run.id,
            )
        )
    db.commit()

    if delivered != len(recipient_ids):
        run.status = "partial" if delivered else run.status
        db.add(run)
        db.commit()

    _maybe_email(db, schedule, run, rows, download)

    _audit_run(db, owner, schedule.id, schedule.report_key,
               len(recipient_ids), delivered, run.status)
    db.commit()
    return {
        "schedule_id": schedule.id,
        "run_id": run.id,
        "report_key": schedule.report_key,
        "rows": len(rows),
        "recipients": len(recipient_ids),
        "delivered": delivered,
        "download": download,
        "job_id": getattr(job, "id", None),
    }


def _audit_run(db: Session, owner, schedule_id: int, report_key: str,
               recipient_count: int, delivered: int, status: str) -> None:
    """Write the audit row every run owes (AC9): action, schedule, recipients.

    ``owner`` may be None for input that never resolved one; the row is
    still written, unattributed.
    """
    from app.core.audit import record_audit

    record_audit(
        db, owner, "export", "report_schedule", schedule_id,
        details=(
            f"report_run schedule={schedule_id} report={report_key} "
            f"owner={getattr(owner, 'id', None)} "
            f"recipients={recipient_count} delivered={delivered} status={status}"
        ),
    )
    db.commit()


def _record_run(db: Session, schedule_id: int, job, *, status: str, payload=None,
                payload_format=None, recipient_count=0, error=None):
    """Get-or-create the run row for this (schedule, job) attempt."""
    from app.models.report_personalization import ReportRun

    run = None
    job_id = getattr(job, "id", None)
    if job_id is not None:
        run = (
            db.query(ReportRun)
            .filter(ReportRun.schedule_id == schedule_id, ReportRun.job_id == job_id)
            .first()
        )
    if run is None:
        run = ReportRun(schedule_id=schedule_id, job_id=job_id)
    run.status = status
    run.payload = payload
    run.payload_format = payload_format
    run.recipient_count = recipient_count
    run.error = error
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _maybe_email(db: Session, schedule, run, rows, download: str) -> None:
    """Email each eligible recipient only when EMAIL_PROVIDER=smtp.

    The default ``log`` provider means in-app only — documented, not a
    failure. An SMTP send failure propagates so the queue retries.
    """
    from app.core.config import settings

    if (settings.EMAIL_PROVIDER or "log").lower() != "smtp":
        return
    import json as _json

    from app.models.user import User
    from app.services.email_provider import get_provider

    recipient_ids = _json.loads(schedule.recipient_ids_json or "[]")
    for recipient_id in recipient_ids:
        recipient = db.query(User).filter(User.id == int(recipient_id)).first()
        if recipient is None or not role_may_view_report(recipient.role, schedule.report_key):
            continue
        to_addr = (recipient.email or "").strip()
        if not to_addr:
            continue
        get_provider().send(
            to_addr,
            f"Scheduled report: {schedule.report_key}",
            f"Scheduled report '{schedule.report_key}' is ready "
            f"({len(rows)} rows). Download: {download}",
        )
