from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.booleans import is_true
from app.models.employee import Employee
from app.models.time_attendance import (
    AttendancePeriodLock,
    TimeCorrectionRequest,
    TimeEntry,
    Timesheet,
)
from app.schemas.time_attendance import (
    PeriodLockCreate,
    TimeCorrectionCreate,
    TimeEntryCreate,
    TimeEntryUpdate,
    TimesheetGenerate,
)

STANDARD_DAY_HOURS = 8.0


class PeriodLockedError(ValueError):
    """Raised when a write targets a work day inside a locked period."""


class PeriodLockNotFoundError(ValueError):
    """Raised when no lock row exists for the requested period."""


def locked_overlap(
    db: Session, period_start: date, period_end: date
) -> AttendancePeriodLock | None:
    """The first locked row overlapping the given range, if any.

    A lock closes every work day from ``period_start`` through
    ``period_end`` inclusive, so any overlap — exact, sub-range, or
    spanning — counts. A row whose lock was reopened is open.
    """
    return (
        db.query(AttendancePeriodLock)
        .filter(
            is_true(AttendancePeriodLock.is_locked),
            AttendancePeriodLock.period_start <= period_end,
            AttendancePeriodLock.period_end >= period_start,
        )
        .first()
    )


def ensure_period_open(db: Session, work_date: date) -> None:
    """Refuse writes for work days that fall inside a locked period.

    A period with no lock row, or whose row was reopened, is open. A
    locked row closes every work day from ``period_start`` through
    ``period_end`` inclusive.
    """
    lock = (
        db.query(AttendancePeriodLock)
        .filter(
            is_true(AttendancePeriodLock.is_locked),
            AttendancePeriodLock.period_start <= work_date,
            AttendancePeriodLock.period_end >= work_date,
        )
        .first()
    )
    if lock is not None:
        raise PeriodLockedError(
            f"Attendance period {lock.period_start}..{lock.period_end} is locked"
        )


def ensure_range_open(db: Session, period_start: date, period_end: date) -> None:
    """Refuse a range write (timesheet generation) when any locked period
    overlaps it — including a lock strictly inside the range, which the
    two endpoint-day checks would miss."""
    lock = locked_overlap(db, period_start, period_end)
    if lock is not None:
        raise PeriodLockedError(
            f"Attendance period {lock.period_start}..{lock.period_end} is locked"
        )


def worked_hours(clock_in: datetime | None, clock_out: datetime | None, break_minutes: int) -> float:
    if not clock_in or not clock_out or clock_out <= clock_in:
        return 0.0
    minutes = (clock_out - clock_in).total_seconds() / 60 - (break_minutes or 0)
    return round(max(minutes, 0) / 60, 2)


def overtime_hours(hours: float) -> float:
    return round(max(hours - STANDARD_DAY_HOURS, 0), 2)


def get_entries(
    db: Session,
    employee_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
) -> list[TimeEntry]:
    query = db.query(TimeEntry)
    if employee_id:
        query = query.filter(TimeEntry.employee_id == employee_id)
    if start:
        query = query.filter(TimeEntry.work_date >= start)
    if end:
        query = query.filter(TimeEntry.work_date <= end)
    return query.order_by(TimeEntry.work_date.desc(), TimeEntry.id.desc()).all()


def get_entry(db: Session, entry_id: int) -> TimeEntry | None:
    return db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()


def get_open_entry(db: Session, employee_id: int) -> TimeEntry | None:
    """The most recent entry that has not been clocked out of yet."""
    return (
        db.query(TimeEntry)
        .filter(TimeEntry.employee_id == employee_id, TimeEntry.clock_out.is_(None))
        .order_by(TimeEntry.id.desc())
        .first()
    )


def create_entry(db: Session, entry_in: TimeEntryCreate) -> TimeEntry:
    ensure_period_open(db, entry_in.work_date)
    hours = worked_hours(entry_in.clock_in, entry_in.clock_out, entry_in.break_minutes)
    db_obj = TimeEntry(
        **entry_in.model_dump(exclude={"clock_out"}),
        clock_out=entry_in.clock_out,
        worked_hours=hours,
        overtime_hours=overtime_hours(hours),
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def clock_in(db: Session, employee_id: int, work_date: date, source: str, notes: str | None) -> TimeEntry:
    ensure_period_open(db, work_date)
    db_obj = TimeEntry(
        employee_id=employee_id,
        work_date=work_date,
        clock_in=datetime.utcnow(),
        source=source,
        notes=notes,
        status="Draft",
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def clock_out(db: Session, entry: TimeEntry) -> TimeEntry:
    ensure_period_open(db, entry.work_date)
    entry.clock_out = datetime.utcnow()
    entry.worked_hours = worked_hours(entry.clock_in, entry.clock_out, entry.break_minutes)
    entry.overtime_hours = overtime_hours(entry.worked_hours)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def update_entry(db: Session, db_obj: TimeEntry, entry_in: TimeEntryUpdate) -> TimeEntry:
    update_data = entry_in.model_dump(exclude_unset=True)
    target_date = update_data.get("work_date", db_obj.work_date)
    ensure_period_open(db, target_date)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db_obj.worked_hours = worked_hours(db_obj.clock_in, db_obj.clock_out, db_obj.break_minutes)
    db_obj.overtime_hours = overtime_hours(db_obj.worked_hours)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_entry(db: Session, db_obj: TimeEntry) -> None:
    ensure_period_open(db, db_obj.work_date)
    db.delete(db_obj)
    db.commit()


def build_timesheet(db: Session, spec: TimesheetGenerate) -> Timesheet:
    ensure_range_open(db, spec.period_start, spec.period_end)
    entries = (
        db.query(TimeEntry)
        .filter(
            TimeEntry.employee_id == spec.employee_id,
            TimeEntry.work_date >= spec.period_start,
            TimeEntry.work_date <= spec.period_end,
        )
        .all()
    )
    total = round(sum(e.worked_hours for e in entries), 2)
    overtime = round(sum(e.overtime_hours for e in entries), 2)

    timesheet = Timesheet(
        employee_id=spec.employee_id,
        period_start=spec.period_start,
        period_end=spec.period_end,
        total_hours=total,
        overtime_hours=overtime,
        entry_count=len(entries),
        status="Draft",
        generated_at=datetime.utcnow(),
    )
    db.add(timesheet)
    db.commit()
    db.refresh(timesheet)
    return timesheet


def get_timesheets(db: Session, employee_id: int | None = None) -> list[Timesheet]:
    query = db.query(Timesheet)
    if employee_id:
        query = query.filter(Timesheet.employee_id == employee_id)
    return query.order_by(Timesheet.period_start.desc(), Timesheet.id.desc()).all()


def get_timesheet(db: Session, timesheet_id: int) -> Timesheet | None:
    return db.query(Timesheet).filter(Timesheet.id == timesheet_id).first()


def submit_timesheet(db: Session, db_obj: Timesheet) -> Timesheet:
    db_obj.status = "Submitted"
    db_obj.submitted_at = datetime.utcnow()
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def approve_timesheet(db: Session, db_obj: Timesheet, approver_id: int) -> Timesheet:
    db_obj.status = "Approved"
    db_obj.approved_by = approver_id
    db_obj.approved_at = datetime.utcnow()
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def attendance_summary(db: Session, day: date) -> dict:
    """Headcount and attendance counts for a given day."""
    employees = db.query(Employee).filter(Employee.status == "Active").count()
    entries = db.query(TimeEntry).filter(TimeEntry.work_date == day).all()
    present = len({e.employee_id for e in entries})
    return {
        "date": day.isoformat(),
        "active_employees": employees,
        "present": present,
        "absent": max(employees - present, 0),
    }


# --- Time corrections ------------------------------------------------------ #


def get_corrections(
    db: Session,
    employee_id: int | None = None,
    status: str | None = None,
) -> list[TimeCorrectionRequest]:
    query = db.query(TimeCorrectionRequest)
    if employee_id:
        query = query.filter(TimeCorrectionRequest.employee_id == employee_id)
    if status:
        query = query.filter(TimeCorrectionRequest.status == status)
    return query.order_by(
        TimeCorrectionRequest.work_date.desc(), TimeCorrectionRequest.id.desc()
    ).all()


def get_correction(db: Session, correction_id: int) -> TimeCorrectionRequest | None:
    return (
        db.query(TimeCorrectionRequest)
        .filter(TimeCorrectionRequest.id == correction_id)
        .first()
    )


def create_correction(
    db: Session, correction_in: TimeCorrectionCreate, requested_by: int | None = None
) -> TimeCorrectionRequest:
    ensure_period_open(db, correction_in.work_date)
    if correction_in.time_entry_id is not None:
        entry = get_entry(db, correction_in.time_entry_id)
        if entry is None:
            raise ValueError("Time entry not found")
        if entry.employee_id != correction_in.employee_id:
            raise ValueError("Time entry does not belong to the employee")
    db_obj = TimeCorrectionRequest(
        **correction_in.model_dump(),
        status="Pending",
        requested_by=requested_by,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def approve_correction(
    db: Session, db_obj: TimeCorrectionRequest, decided_by: int
) -> TimeCorrectionRequest:
    if db_obj.status != "Pending":
        raise ValueError("Only pending corrections can be approved")
    ensure_period_open(db, db_obj.work_date)
    entry = (
        get_entry(db, db_obj.time_entry_id)
        if db_obj.time_entry_id is not None
        else None
    )
    if entry is None:
        entry = (
            db.query(TimeEntry)
            .filter(
                TimeEntry.employee_id == db_obj.employee_id,
                TimeEntry.work_date == db_obj.work_date,
            )
            .order_by(TimeEntry.id.desc())
            .first()
        )
    if entry is None:
        raise ValueError("No time entry exists for the correction's work day")
    before_clock_in = entry.clock_in
    before_clock_out = entry.clock_out
    if db_obj.requested_clock_in is not None:
        entry.clock_in = db_obj.requested_clock_in
    if db_obj.requested_clock_out is not None:
        entry.clock_out = db_obj.requested_clock_out
    entry.worked_hours = worked_hours(entry.clock_in, entry.clock_out, entry.break_minutes)
    entry.overtime_hours = overtime_hours(entry.worked_hours)
    db_obj.status = "Approved"
    db_obj.decided_by = decided_by
    db_obj.decided_at = datetime.utcnow()
    db.add(entry)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    # Transient (unmapped) before-snapshot for the caller: the endpoint
    # persists it into the approval's audit details, so the overwritten
    # times stay reviewable after the entry is changed.
    db_obj._applied_entry_id = entry.id  # type: ignore[attr-defined]
    db_obj._before_clock_in = before_clock_in  # type: ignore[attr-defined]
    db_obj._before_clock_out = before_clock_out  # type: ignore[attr-defined]
    return db_obj


def reject_correction(
    db: Session, db_obj: TimeCorrectionRequest, decided_by: int
) -> TimeCorrectionRequest:
    if db_obj.status != "Pending":
        raise ValueError("Only pending corrections can be rejected")
    db_obj.status = "Rejected"
    db_obj.decided_by = decided_by
    db_obj.decided_at = datetime.utcnow()
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


# --- Attendance period locks ----------------------------------------------- #


def get_period_lock(
    db: Session, period_start: date, period_end: date
) -> AttendancePeriodLock | None:
    return (
        db.query(AttendancePeriodLock)
        .filter(
            AttendancePeriodLock.period_start == period_start,
            AttendancePeriodLock.period_end == period_end,
        )
        .first()
    )


def period_is_locked(db: Session, period_start: date, period_end: date) -> bool:
    return locked_overlap(db, period_start, period_end) is not None


def lock_period(db: Session, spec: PeriodLockCreate, locked_by: int | None = None) -> AttendancePeriodLock:
    if spec.period_end < spec.period_start:
        raise ValueError("period_end must be after period_start")
    existing = get_period_lock(db, spec.period_start, spec.period_end)
    if existing is not None:
        existing.is_locked = True
        existing.locked_by = locked_by
        existing.locked_at = datetime.utcnow()
        existing.reopened_by = None
        existing.reopened_at = None
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    db_obj = AttendancePeriodLock(
        period_start=spec.period_start,
        period_end=spec.period_end,
        is_locked=True,
        locked_by=locked_by,
        locked_at=datetime.utcnow(),
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def reopen_period(db: Session, spec: PeriodLockCreate, reopened_by: int | None = None) -> AttendancePeriodLock:
    existing = get_period_lock(db, spec.period_start, spec.period_end)
    if existing is None:
        raise PeriodLockNotFoundError("No locked period exists for the given dates")
    if not existing.is_locked:
        raise ValueError("Period is already open for the given dates")
    existing.is_locked = False
    existing.reopened_by = reopened_by
    existing.reopened_at = datetime.utcnow()
    db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing
