from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, MANAGER_ROLES, WORKFORCE_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.errors import conflict
from app.core.visibility import ensure_can_view_employee
from app.core.visibility import (
    apply_visibility,
    ensure_can_view_employee,
    ensure_can_view_employee_or_403,
)
from app.crud import crud_time_attendance as crud
from app.crud.crud_time_attendance import PeriodLockedError, PeriodLockNotFoundError
from app.crud.crud_employee import get_employee
from app.models.user import User
from app.schemas.time_attendance import (
    ClockIn,
    ClockOut,
    PeriodLockCreate,
    PeriodLockOut,
    PeriodStatusOut,
    TimeCorrectionCreate,
    TimeCorrectionOut,
    TimeEntryCreate,
    TimeEntryOut,
    TimeEntryUpdate,
    TimesheetGenerate,
    TimesheetOut,
)
from app.models.time_attendance import TimeCorrectionRequest, TimeEntry, Timesheet

router = APIRouter()


def _period_locked(exc: PeriodLockedError) -> None:
    """A locked period is a conflict, not a crash: name the period."""
    raise conflict("attendance_period_locked", str(exc))


@router.get("/entries", response_model=list[TimeEntryOut], operation_id="timeListEntries")
def list_entries(
    employee_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    q = db.query(TimeEntry)
    if employee_id:
        ensure_can_view_employee(db, current_user, employee_id)
        q = q.filter(TimeEntry.employee_id == employee_id)
    else:
        q = apply_visibility(q, TimeEntry.employee_id, current_user, db)
    if start:
        q = q.filter(TimeEntry.work_date >= start)
    if end:
        q = q.filter(TimeEntry.work_date <= end)
    return q.order_by(TimeEntry.work_date.desc(), TimeEntry.id.desc()).all()


@router.get("/entries/{entry_id}", response_model=TimeEntryOut, operation_id="timeGetTimeentries")
def get_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    entry = crud.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    ensure_can_view_employee(db, current_user, entry.employee_id)
    return entry


@router.post("/clock-in", response_model=TimeEntryOut, status_code=201, operation_id="timeClockIn")
def clock_in(
    payload: ClockIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    employee = get_employee(db, payload.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if crud.get_open_entry(db, payload.employee_id):
        raise HTTPException(status_code=400, detail="Already clocked in")
    try:
        entry = crud.clock_in(
            db,
            employee_id=payload.employee_id,
            work_date=payload.work_date or date.today(),
            source=payload.source,
            notes=payload.notes,
        )
    except PeriodLockedError as exc:
        _period_locked(exc)
    record_audit(db, current_user, "clock_in", "TimeEntry", entry.id)
    db.commit()
    return entry


@router.post("/clock-out", response_model=TimeEntryOut, status_code=201, operation_id="timeClockOut")
def clock_out(
    payload: ClockOut,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    entry = crud.get_open_entry(db, payload.employee_id)
    if not entry:
        raise HTTPException(status_code=400, detail="No open time entry to clock out")
    if payload.notes:
        entry.notes = payload.notes
    try:
        entry = crud.clock_out(db, entry)
    except PeriodLockedError as exc:
        _period_locked(exc)
    record_audit(db, current_user, "clock_out", "TimeEntry", entry.id)
    db.commit()
    return entry


@router.get("/today", operation_id="timeGetTimetoday")
def today(
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    if employee_id:
        ensure_can_view_employee(db, current_user, employee_id)
    return crud.attendance_summary(db, date.today())


@router.post("/entries", response_model=TimeEntryOut, status_code=201, operation_id="timeCreateTimeentries")
def create_entry(
    payload: TimeEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    try:
        entry = crud.create_entry(db, payload)
    except PeriodLockedError as exc:
        _period_locked(exc)
    record_audit(db, current_user, "create_time_entry", "TimeEntry", entry.id)
    db.commit()
    return entry


@router.put("/entries/{entry_id}", response_model=TimeEntryOut, operation_id="timeUpdateTimeentries")
def update_entry(
    entry_id: int,
    payload: TimeEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    entry = crud.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    try:
        entry = crud.update_entry(db, entry, payload)
    except PeriodLockedError as exc:
        _period_locked(exc)
    record_audit(db, current_user, "update_time_entry", "TimeEntry", entry.id)
    db.commit()
    return entry


@router.delete("/entries/{entry_id}", operation_id="timeDeleteTimeentries")
def delete_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    entry = crud.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    try:
        crud.delete_entry(db, entry)
    except PeriodLockedError as exc:
        _period_locked(exc)
    record_audit(db, current_user, "delete_time_entry", "TimeEntry", entry_id)
    db.commit()
    return {"msg": "deleted"}


# --- Timesheets ------------------------------------------------------------ #

@router.get("/timesheets", response_model=list[TimesheetOut], operation_id="timeListTimesheets")
def list_timesheets(
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    q = db.query(Timesheet)
    q = apply_visibility(q, Timesheet.employee_id, current_user, db)
    if employee_id:
        ensure_can_view_employee(db, current_user, employee_id)
        q = q.filter(Timesheet.employee_id == employee_id)
    return q.all()


@router.get("/timesheets/{timesheet_id}", response_model=TimesheetOut, operation_id="timeGetTimetimesheets")
def get_timesheet(
    timesheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    timesheet = crud.get_timesheet(db, timesheet_id)
    if not timesheet:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    ensure_can_view_employee(db, current_user, timesheet.employee_id)
    return timesheet


@router.post("/timesheets/generate", response_model=TimesheetOut, status_code=201, operation_id="timeCreateTimetimesheetsgenerate")
def generate_timesheet(
    payload: TimesheetGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    if payload.period_end < payload.period_start:
        raise HTTPException(status_code=400, detail="period_end must be after period_start")
    if not get_employee(db, payload.employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    try:
        timesheet = crud.build_timesheet(db, payload)
    except PeriodLockedError as exc:
        _period_locked(exc)
    record_audit(db, current_user, "generate_timesheet", "Timesheet", timesheet.id)
    db.commit()
    return timesheet


@router.post("/timesheets/{timesheet_id}/submit", response_model=TimesheetOut, operation_id="timeSubmitTimesheet")
def submit_timesheet(
    timesheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    timesheet = crud.get_timesheet(db, timesheet_id)
    if not timesheet:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    ensure_can_view_employee(db, current_user, timesheet.employee_id)
    timesheet = crud.submit_timesheet(db, timesheet)
    record_audit(db, current_user, "submit_timesheet", "Timesheet", timesheet.id)
    db.commit()
    return timesheet


@router.post("/timesheets/{timesheet_id}/approve", response_model=TimesheetOut, operation_id="timeApproveTimesheet")
def approve_timesheet(
    timesheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    timesheet = crud.get_timesheet(db, timesheet_id)
    if not timesheet:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    # A manager approves the timesheets of their own reporting line and
    # nothing else.
    ensure_can_view_employee_or_403(db, current_user, timesheet.employee_id)
    timesheet = crud.approve_timesheet(db, timesheet, current_user.id)
    record_audit(db, current_user, "approve_timesheet", "Timesheet", timesheet.id)
    db.commit()
    return timesheet


# --- Time corrections ------------------------------------------------------ #


@router.post("/corrections", response_model=TimeCorrectionOut, status_code=201, operation_id="timeCreateCorrection")
def create_correction(
    payload: TimeCorrectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    ensure_can_view_employee(db, current_user, payload.employee_id)
    if payload.time_entry_id is not None and payload.time_entry_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid time entry")
    try:
        correction = crud.create_correction(
            db, payload, requested_by=current_user.id
        )
    except PeriodLockedError as exc:
        _period_locked(exc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    record_audit(db, current_user, "create_time_correction", "TimeCorrectionRequest", correction.id)
    db.commit()
    return correction


@router.get("/corrections", response_model=list[TimeCorrectionOut], operation_id="timeListCorrections")
def list_corrections(
    employee_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    q = db.query(TimeCorrectionRequest)
    q = apply_visibility(q, TimeCorrectionRequest.employee_id, current_user, db)
    if employee_id:
        ensure_can_view_employee(db, current_user, employee_id)
        q = q.filter(TimeCorrectionRequest.employee_id == employee_id)
    if status:
        q = q.filter(TimeCorrectionRequest.status == status)
    return q.order_by(
        TimeCorrectionRequest.work_date.desc(), TimeCorrectionRequest.id.desc()
    ).all()


@router.post("/corrections/{correction_id}/approve", response_model=TimeCorrectionOut, operation_id="timeApproveCorrection")
def approve_correction(
    correction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    correction = crud.get_correction(db, correction_id)
    if not correction:
        raise HTTPException(status_code=404, detail="Time correction not found")
    # A manager decides the corrections of their own reporting line and
    # nothing else.
    ensure_can_view_employee_or_403(db, current_user, correction.employee_id)
    if correction.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending corrections can be approved")
    try:
        correction = crud.approve_correction(db, correction, current_user.id)
    except PeriodLockedError as exc:
        _period_locked(exc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    details = (
        f"time_entry_id={getattr(correction, '_applied_entry_id', correction.time_entry_id)} "
        f"before_clock_in={getattr(correction, '_before_clock_in', None)} "
        f"before_clock_out={getattr(correction, '_before_clock_out', None)} "
        f"requested_clock_in={correction.requested_clock_in} "
        f"requested_clock_out={correction.requested_clock_out}"
    )
    record_audit(db, current_user, "approve_time_correction", "TimeCorrectionRequest", correction.id, details=details)
    db.commit()
    return correction


@router.post("/corrections/{correction_id}/reject", response_model=TimeCorrectionOut, operation_id="timeRejectCorrection")
def reject_correction(
    correction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    correction = crud.get_correction(db, correction_id)
    if not correction:
        raise HTTPException(status_code=404, detail="Time correction not found")
    # The same reporting-line scope as the approval above.
    ensure_can_view_employee_or_403(db, current_user, correction.employee_id)
    if correction.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending corrections can be rejected")
    try:
        correction = crud.reject_correction(db, correction, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    record_audit(db, current_user, "reject_time_correction", "TimeCorrectionRequest", correction.id)
    db.commit()
    return correction


# --- Attendance period locks ----------------------------------------------- #


@router.post("/period-locks/lock", response_model=PeriodLockOut, status_code=201, operation_id="timeLockPeriod")
def lock_period(
    payload: PeriodLockCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    try:
        lock = crud.lock_period(db, payload, locked_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    record_audit(db, current_user, "lock_attendance_period", "AttendancePeriodLock", lock.id)
    db.commit()
    return lock


@router.post("/period-locks/reopen", response_model=PeriodLockOut, operation_id="timeReopenPeriod")
def reopen_period(
    payload: PeriodLockCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    try:
        lock = crud.reopen_period(db, payload, reopened_by=current_user.id)
    except PeriodLockNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    record_audit(db, current_user, "reopen_attendance_period", "AttendancePeriodLock", lock.id)
    db.commit()
    return lock


@router.get("/period-locks/status", response_model=PeriodStatusOut, operation_id="timePeriodLockStatus")
def period_lock_status(
    period_start: date,
    period_end: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    return {
        "period_start": period_start,
        "period_end": period_end,
        "is_locked": crud.period_is_locked(db, period_start, period_end),
    }
