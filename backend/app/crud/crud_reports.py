from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.department import Department
from app.models.employee import Employee
from app.models.leave import LeaveBalance, LeaveRequest
from app.models.recruiting import Candidate, JobRequisition, Offer
from app.models.scheduling import ShiftSwap
from app.models.time_attendance import TimeEntry, Timesheet
from app.models.user import User


def _audit_dict(entry: AuditLog) -> dict:
    return {
        "id": entry.id,
        "actor_id": entry.actor_id,
        "actor_name": entry.actor_name,
        "action": entry.action,
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id,
        "details": entry.details,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


def dashboard(db: Session) -> dict:
    active = db.query(func.count(Employee.id)).filter(Employee.status == "Active").scalar()
    terminated = (
        db.query(func.count(Employee.id)).filter(Employee.status == "Terminated").scalar()
    )
    pending_leave = (
        db.query(func.count(LeaveRequest.id)).filter(LeaveRequest.status == "Pending").scalar()
    )
    pending_timesheets = (
        db.query(func.count(Timesheet.id)).filter(Timesheet.status == "Submitted").scalar()
    )
    pending_swaps = db.query(func.count(ShiftSwap.id)).filter(ShiftSwap.status == "Pending").scalar()

    return {
        "employees": {
            "active": active,
            "terminated": terminated,
            "total": (active or 0) + (terminated or 0),
        },
        "recruiting": {
            "open_requisitions": db.query(func.count(JobRequisition.id))
            .filter(JobRequisition.status == "Open")
            .scalar(),
            "candidates": db.query(func.count(Candidate.id)).scalar(),
            "offers": db.query(func.count(Offer.id)).scalar(),
        },
        "approvals": {
            "pending_leave": pending_leave,
            "pending_timesheets": pending_timesheets,
            "pending_shift_swaps": pending_swaps,
        },
        "attendance_today": attendance(db, date.today()),
        "recent_audit": [_audit_dict(a) for a in recent_audit(db, limit=10)],
    }


def headcount_report(db: Session) -> dict:
    rows = (
        db.query(Department.name, func.count(Employee.id))
        .outerjoin(Employee, Employee.department_id == Department.id)
        .group_by(Department.name)
        .order_by(Department.name)
        .all()
    )
    by_status = dict(
        db.query(Employee.status, func.count(Employee.id))
        .group_by(Employee.status)
        .all()
    )
    return {
        "by_department": [{"department": name, "employees": count} for name, count in rows],
        "by_status": by_status,
        "total": sum(by_status.values()),
    }


def leave_report(db: Session) -> dict:
    rows = (
        db.query(LeaveRequest.status, func.count(LeaveRequest.id))
        .group_by(LeaveRequest.status)
        .all()
    )
    entitled = db.query(func.coalesce(func.sum(LeaveBalance.entitled_days), 0)).scalar()
    used = db.query(func.coalesce(func.sum(LeaveBalance.used_days), 0)).scalar()
    return {
        "by_status": dict(rows),
        "entitled_days_total": float(entitled or 0),
        "used_days_total": float(used or 0),
    }


def labor_cost_report(db: Session) -> dict:
    rows = (
        db.query(Department.name, func.count(Employee.id), func.coalesce(func.sum(Employee.salary), 0))
        .outerjoin(Employee, Employee.department_id == Department.id)
        .group_by(Department.name)
        .order_by(Department.name)
        .all()
    )
    total = db.query(func.coalesce(func.sum(Employee.salary), 0)).filter(
        Employee.status == "Active"
    ).scalar()
    return {
        "monthly_payroll": float(total or 0),
        "by_department": [
            {
                "department": name,
                "employees": count,
                "monthly_cost": float(cost or 0),
            }
            for name, count, cost in rows
        ],
    }


def attendance(db: Session, day: date) -> dict:
    entries = db.query(TimeEntry).filter(TimeEntry.work_date == day).all()
    total_hours = round(sum(e.worked_hours for e in entries), 2)
    overtime = round(sum(e.overtime_hours for e in entries), 2)
    return {
        "date": day.isoformat(),
        "present": len({e.employee_id for e in entries}),
        "total_hours": total_hours,
        "overtime_hours": overtime,
    }


def recent_audit(db: Session, limit: int = 50) -> list[AuditLog]:
    return (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )


def audit_report(db: Session, limit: int = 100) -> list[AuditLog]:
    return recent_audit(db, limit=limit)


def users_report(db: Session) -> dict:
    by_role = dict(db.query(User.role, func.count(User.id)).group_by(User.role).all())
    return {"by_role": by_role, "total": sum(by_role.values())}


# --------------------------------------------------------------------------
# Workforce movement — joiners / leavers / attrition (LP-REP-001)
#
# Read-only queries over stored employment facts (hire_date,
# termination_date, status). No payroll engine call, no recomputation, no
# migration: the filters name columns that already exist. Employees carry
# no location column, so the location filter is resolved through
# positions: an employee counts for a location when their department holds
# at least one position at that location.
# --------------------------------------------------------------------------


def _department_ids_for_location(db: Session, location_id: int) -> set[int]:
    """Departments holding at least one position at ``location_id``."""
    from app.models.core_hr import Position

    return {
        row[0]
        for row in db.query(Position.department_id)
        .filter(Position.location_id == location_id)
        .distinct()
        .all()
    }


def _movement_base_query(
    db: Session,
    *,
    entity_id: int | None = None,
    department_id: int | None = None,
    location_id: int | None = None,
    visible_ids: set[int] | None = None,
):
    """Shared scoping for joiners/leavers: entity/dept/location + visibility."""
    if visible_ids is not None and not visible_ids:
        return None
    q = db.query(Employee)
    if entity_id is not None:
        q = q.filter(Employee.legal_entity_id == entity_id)
    if department_id is not None:
        q = q.filter(Employee.department_id == department_id)
    if location_id is not None:
        dept_ids = _department_ids_for_location(db, location_id)
        if not dept_ids:
            return None
        q = q.filter(Employee.department_id.in_(dept_ids))
    if visible_ids is not None:
        q = q.filter(Employee.id.in_(visible_ids))
    return q


def _movement_row(emp: Employee) -> dict:
    dept = getattr(emp, "department", None)
    entity = getattr(emp, "legal_entity", None)
    return {
        "id": emp.id,
        "employee_id": emp.employee_id,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "email": emp.email,
        "hire_date": emp.hire_date.isoformat() if emp.hire_date else None,
        "termination_date": emp.termination_date.isoformat() if emp.termination_date else None,
        "status": emp.status,
        "department_id": emp.department_id,
        "department": getattr(dept, "name", None),
        "legal_entity_id": emp.legal_entity_id,
        "legal_entity": getattr(entity, "name", None),
    }


def joiners_report(
    db: Session,
    *,
    from_date,
    to_date,
    entity_id: int | None = None,
    department_id: int | None = None,
    location_id: int | None = None,
    visible_ids: set[int] | None = None,
) -> list[dict]:
    """Employees hired in ``[from_date, to_date]`` under the given filters."""
    q = _movement_base_query(
        db,
        entity_id=entity_id,
        department_id=department_id,
        location_id=location_id,
        visible_ids=visible_ids,
    )
    if q is None:
        return []
    rows = (
        q.filter(Employee.hire_date >= from_date, Employee.hire_date <= to_date)
        .order_by(Employee.hire_date.asc(), Employee.id.asc())
        .all()
    )
    return [_movement_row(e) for e in rows]


def leavers_report(
    db: Session,
    *,
    from_date,
    to_date,
    entity_id: int | None = None,
    department_id: int | None = None,
    location_id: int | None = None,
    visible_ids: set[int] | None = None,
) -> list[dict]:
    """Employees terminated in ``[from_date, to_date]`` under the given filters."""
    q = _movement_base_query(
        db,
        entity_id=entity_id,
        department_id=department_id,
        location_id=location_id,
        visible_ids=visible_ids,
    )
    if q is None:
        return []
    rows = (
        q.filter(
            Employee.termination_date.is_not(None),
            Employee.termination_date >= from_date,
            Employee.termination_date <= to_date,
        )
        .order_by(Employee.termination_date.asc(), Employee.id.asc())
        .all()
    )
    return [_movement_row(e) for e in rows]


def _headcount_on(
    db: Session,
    day,
    *,
    entity_id: int | None = None,
    department_id: int | None = None,
    location_id: int | None = None,
    visible_ids: set[int] | None = None,
) -> int:
    """Headcount employed on ``day``: hired on/before, not terminated before."""
    q = _movement_base_query(
        db,
        entity_id=entity_id,
        department_id=department_id,
        location_id=location_id,
        visible_ids=visible_ids,
    )
    if q is None:
        return 0
    return (
        q.filter(
            Employee.hire_date <= day,
            (Employee.termination_date.is_(None)) | (Employee.termination_date > day),
        ).count()
    )


def attrition_report(
    db: Session,
    *,
    year: int,
    entity_id: int | None = None,
    department_id: int | None = None,
    location_id: int | None = None,
    visible_ids: set[int] | None = None,
) -> dict:
    """Annualised attrition from stored facts only.

    ``attrition_pct = leavers_in_year / average_headcount * 100`` where the
    average is the mean of the headcount on Jan 1 and on Dec 31. A zero
    average yields 0.0 rather than a division error.
    """
    from datetime import date as _date

    start = _date(year, 1, 1)
    end = _date(year, 12, 31)
    scope = dict(
        entity_id=entity_id,
        department_id=department_id,
        location_id=location_id,
        visible_ids=visible_ids,
    )
    joiners = joiners_report(db, from_date=start, to_date=end, **scope)
    leavers = leavers_report(db, from_date=start, to_date=end, **scope)
    opening = _headcount_on(db, start, **scope)
    closing = _headcount_on(db, end, **scope)
    average = (opening + closing) / 2
    pct = round(len(leavers) / average * 100, 2) if average else 0.0
    return {
        "year": year,
        "joiners": len(joiners),
        "leavers": len(leavers),
        "headcount_start": opening,
        "headcount_end": closing,
        "average_headcount": average,
        "attrition_pct": pct,
        "definition": (
            "attrition_pct = leavers with a termination_date in the year / "
            "average of headcount on Jan 1 and Dec 31 * 100"
        ),
        "filters": {
            "entity_id": entity_id,
            "department_id": department_id,
            "location_id": location_id,
        },
    }
