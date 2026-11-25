"""Demand series builder."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.job import Job
from app.models.core_hr import Location, Position
from app.models.time_attendance import TimeEntry
from app.models.leave import LeaveRequest
from app.models.scheduling import RosterEntry


HOURS_PER_LEAVE_DAY = 8.0


class DemandPoint(dict):
    def __init__(
        self,
        *,
        date: date,
        value: float,
        location_id: Optional[int] = None,
        location_code: Optional[str] = None,
        role_id: Optional[int] = None,
        role: Optional[str] = None,
        role_code: Optional[str] = None,
        actual_hours: float = 0.0,
        leave_hours: float = 0.0,
        scheduled_hours: float = 0.0,
        source: str = "history",
        lower_bound: Optional[float] = None,
        upper_bound: Optional[float] = None,
        forecast_run_id: Optional[int] = None,
    ) -> None:
        super().__init__(
            date=date,
            value=round(float(value), 4),
            location_id=location_id,
            location_code=location_code,
            role_id=role_id,
            role=role,
            role_code=role_code,
            actual_hours=round(float(actual_hours), 4),
            leave_hours=round(float(leave_hours), 4),
            scheduled_hours=round(float(scheduled_hours), 4),
            source=source,
            lower_bound=round(float(lower_bound), 4) if lower_bound is not None else None,
            upper_bound=round(float(upper_bound), 4) if upper_bound is not None else None,
            forecast_run_id=forecast_run_id,
        )
        self.date = date
        self.value = round(float(value), 4)
        self.location_id = location_id
        self.location_code = location_code
        self.role_id = role_id
        self.role = role
        self.role_code = role_code
        self.actual_hours = round(float(actual_hours), 4)
        self.leave_hours = round(float(leave_hours), 4)
        self.scheduled_hours = round(float(scheduled_hours), 4)
        self.source = source
        self.lower_bound = round(float(lower_bound), 4) if lower_bound is not None else None
        self.upper_bound = round(float(upper_bound), 4) if upper_bound is not None else None
        self.forecast_run_id = forecast_run_id
        self.hours = self.value

    def as_dict(self) -> dict:
        return dict(self)


def _daterange(start: date, end: date):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def _matching_employees(db: Session, location_id: Optional[int], role: Any) -> list[int]:
    q = db.query(Employee)
    if isinstance(role, int):
        q = q.filter(Employee.job_id == role)
    elif isinstance(role, str) and role:
        q = q.join(Job, Employee.job_id == Job.id).filter(
            (Job.title == role) | (Job.code == role)
        )
    if location_id is not None:
        job_ids = [
            r[0]
            for r in db.query(Position.job_id)
            .filter(Position.location_id == location_id)
            .all()
        ]
        if job_ids:
            q = q.filter(Employee.job_id.in_(job_ids))
    return [e.id for e in q.all()]


def _scheduled_hours_for(entry: RosterEntry) -> float:
    try:
        start = datetime.strptime(entry.start_time, "%H:%M")
        end = datetime.strptime(entry.end_time, "%H:%M")
    except (ValueError, TypeError):
        return 0.0
    delta = (end - start).total_seconds() / 3600.0
    if delta < 0:
        delta += 24.0
    break_minutes = 0
    template = getattr(entry, "shift_template", None)
    if template is not None:
        break_minutes = getattr(template, "break_minutes", 0) or 0
    return max(delta - (break_minutes or 0) / 60.0, 0.0)


def build_demand_series(
    db: Session,
    *,
    start_date: date,
    end_date: date,
    location_id: Optional[int] = None,
    role: Any = None,
    job_id: Optional[int] = None,
    include_time_entries: bool = True,
    include_leave: bool = True,
    include_roster: bool = True,
    approved_time_only: bool = True,
    approved_leave_only: bool = True,
    hours_per_leave_day: float = HOURS_PER_LEAVE_DAY,
    source: str = "history",
) -> list[DemandPoint]:
    if isinstance(job_id, int) and role is None:
        role = job_id

    employee_ids = _matching_employees(db, location_id, role)
    employee_set = set(employee_ids)

    location_code = None
    if location_id is not None:
        loc = db.query(Location).filter(Location.id == location_id).first()
        if loc is not None:
            location_code = loc.code

    role_label = None
    role_code = None
    role_id = role if isinstance(role, int) else None
    if isinstance(role, int):
        job = db.query(Job).filter(Job.id == role).first()
        if job is not None:
            role_label = job.title
            role_code = job.code
    elif isinstance(role, str) and role:
        job = db.query(Job).filter((Job.title == role) | (Job.code == role)).first()
        if job is not None:
            role_label = job.title
            role_code = job.code
            role_id = job.id

    time_entries = []
    if include_time_entries:
        q = db.query(TimeEntry).filter(
            TimeEntry.work_date >= start_date,
            TimeEntry.work_date <= end_date,
        )
        if employee_set:
            q = q.filter(TimeEntry.employee_id.in_(employee_set))
        time_entries = q.all()
        if approved_time_only:
            time_entries = [e for e in time_entries if (e.status or "") == "Approved"]

    leave_requests = []
    if include_leave:
        q = db.query(LeaveRequest).filter(
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
        if employee_set:
            q = q.filter(LeaveRequest.employee_id.in_(employee_set))
        leave_requests = q.all()
        if approved_leave_only:
            leave_requests = [r for r in leave_requests if (r.status or "") == "Approved"]

    roster_entries = []
    if include_roster:
        q = db.query(RosterEntry).filter(
            RosterEntry.work_date >= start_date,
            RosterEntry.work_date <= end_date,
        )
        if employee_set:
            q = q.filter(RosterEntry.employee_id.in_(employee_set))
        roster_entries = q.all()

    actual_by_date = {}
    for e in time_entries:
        actual_by_date[e.work_date] = actual_by_date.get(e.work_date, 0.0) + float(e.worked_hours or 0)

    leave_by_date = {}
    for lr in leave_requests:
        for d in _daterange(max(lr.start_date, start_date), min(lr.end_date, end_date)):
            if d.weekday() < 5:
                leave_by_date[d] = leave_by_date.get(d, 0.0) + float(hours_per_leave_day)

    roster_by_date = {}
    for re_ in roster_entries:
        roster_by_date[re_.work_date] = roster_by_date.get(re_.work_date, 0.0) + _scheduled_hours_for(re_)

    out = []
    for d in _daterange(start_date, end_date):
        actual = actual_by_date.get(d, 0.0) if include_time_entries else 0.0
        leave = leave_by_date.get(d, 0.0) if include_leave else 0.0
        sched = roster_by_date.get(d, 0.0) if include_roster else 0.0
        total = actual + leave + sched
        out.append(
            DemandPoint(
                date=d,
                value=total,
                location_id=location_id,
                location_code=location_code,
                role_id=role_id,
                role=role_label,
                role_code=role_code,
                actual_hours=actual,
                leave_hours=leave,
                scheduled_hours=sched,
                source=source,
            )
        )
    return out


build_series = build_demand_series
get_demand_series = build_demand_series
demand_series = build_demand_series
build_demand = build_demand_series


class DemandSeriesBuilder:
    def __init__(self, db: Session):
        self.db = db

    def build(self, start_date: date, end_date: date, *, location_id=None, role=None, **kwargs):
        return build_demand_series(
            self.db, start_date=start_date, end_date=end_date,
            location_id=location_id, role=role, **kwargs,
        )

    build_series = build
    build_demand_series = build
    run = build


def DemandSeries(*args, **kwargs):
    return build_demand_series(*args, **kwargs)
