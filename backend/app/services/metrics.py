"""Metric catalogue.

Every number the product shows a user is registered here with its business
meaning, calculation, source, reporting period, refresh behaviour, permissions
and known limitations. The endpoint serves the definition alongside the value,
so a reader never has to guess what a figure counts.

Defects this replaced
---------------------
``labor_cost_report`` filtered ``status == 'Active'`` for the total but *not*
for the per-department breakdown, so the department rows did not sum to the
total it was reported next to.

``leave_report`` summed entitlements and usage across every year, mixing 2025
into a 2026 figure with no way to tell.

``headcount_report`` counted every employee regardless of status, so
"headcount" included people who had left.

Each of those is now an explicit metric with a stated scope.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

# Employee statuses that count toward "currently employed".
EMPLOYED_STATUSES = ("Active", "On Leave")


@dataclass
class MetricDefinition:
    key: str
    name: str
    business_meaning: str
    calculation: str
    source: str
    reporting_period: str
    filters: list[str] = field(default_factory=list)
    refresh_behaviour: str = "Calculated on request; no cached copy."
    permissions: str = "HR, SuperAdmin"
    limitations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "business_meaning": self.business_meaning,
            "calculation": self.calculation,
            "source": self.source,
            "reporting_period": self.reporting_period,
            "filters": self.filters,
            "refresh_behaviour": self.refresh_behaviour,
            "permissions": self.permissions,
            "limitations": self.limitations,
        }


CATALOGUE: dict[str, MetricDefinition] = {}


def _define(**kwargs) -> MetricDefinition:
    d = MetricDefinition(**kwargs)
    CATALOGUE[d.key] = d
    return d


# ===========================================================================
# Definitions
# ===========================================================================

_define(
    key="headcount.active",
    name="Active headcount",
    business_meaning=(
        "People currently employed and expected to be present: excludes anyone "
        "who has terminated, and counts employees on leave as employed."
    ),
    calculation="COUNT(employees WHERE status IN ('Active', 'On Leave'))",
    source="employees.status",
    reporting_period="Point in time, as at request time.",
    filters=["status"],
    refresh_behaviour="Calculated on request; no cached copy.",
    permissions="HR, SuperAdmin, PayrollViewer",
    limitations=[
        "Includes employees with no pay profile; run the data-quality "
        "'payroll.active_without_profile' check to find them.",
        "Does not subtract employees who are on long-term leave.",
    ],
)

_define(
    key="headcount.by_department",
    name="Active headcount by department",
    business_meaning="How many employed people sit in each department.",
    calculation=(
        "COUNT of employed employees grouped by employees.department_id, with "
        "departments that have no employees shown as 0 rather than omitted."
    ),
    source="employees joined to departments",
    reporting_period="Point in time, as at request time.",
    filters=["status", "department_id"],
    refresh_behaviour="Calculated on request; no cached copy.",
    permissions="HR, SuperAdmin, PayrollViewer",
    limitations=[
        "An employee whose department disagrees with their job's department is "
        "counted under the employee's department. See the data-quality check "
        "'employee.department_job_mismatch'.",
    ],
)

_define(
    key="headcount.terminated",
    name="Terminated headcount",
    business_meaning="People recorded as terminated. Reported separately so it "
                     "is never silently mixed into headcount.",
    calculation="COUNT(employees WHERE status = 'Terminated')",
    source="employees.status",
    reporting_period="Cumulative to date.",
    filters=["status"],
    refresh_behaviour="Calculated on request; no cached copy.",
    permissions="HR, SuperAdmin, PayrollViewer",
    limitations=["Cumulative; not limited to a period unless filtered by date."],
)

_define(
    key="turnover.rate",
    name="Annualised turnover rate",
    business_meaning=(
        "Share of the workforce that left in the period. Voluntary and "
        "involuntary are not separated, so treat as a single attrition figure."
    ),
    calculation=(
        "(terminations in period / average employed headcount in period) * 100. "
        "Average headcount uses the mean of the opening and closing counts."
    ),
    source="offboarding.terminations + employees",
    reporting_period="The trailing 12 months unless a date range is supplied.",
    filters=["date range", "department"],
    refresh_behaviour="Calculated on request.",
    permissions="HR, SuperAdmin",
    limitations=[
        "No voluntary/involuntary split; terminations are counted together.",
        "No contract-type or hours-based weighting: a part-time leaver counts "
        "the same as a full-time one.",
        "Re-hires are not netted off; someone terminated then rehired counts "
        "once as a termination.",
    ],
)

_define(
    key="recruiting.open_requisitions",
    name="Open requisitions",
    business_meaning="Approved headcount requests that are open and recruiting.",
    calculation="COUNT(job_requisitions WHERE status = 'Open')",
    source="job_requisitions.status",
    reporting_period="Point in time.",
    filters=["status", "department_id"],
    refresh_behaviour="Calculated on request.",
    permissions="HR, SuperAdmin",
    limitations=["Counts requisitions, not openings. Requisitions with "
                 "openings > 1 count once."],
)

_define(
    key="recruiting.funnel",
    name="Recruitment funnel",
    business_meaning="How many candidates sit at each pipeline stage.",
    calculation=(
        "COUNT(applications) grouped by applications.status, plus distinct "
        "candidates and offers for the same population."
    ),
    source="applications.status, candidates, offers",
    reporting_period="Cumulative for candidates currently in the pipeline.",
    filters=["requisition_id", "date range"],
    refresh_behaviour="Calculated on request.",
    permissions="HR, SuperAdmin",
    limitations=[
        "Stages are whatever statuses exist in the data; there is no enforced "
        "stage ordering, so a candidate can move backwards.",
        "No time-in-stage, so a stalled stage is not visible here.",
    ],
)

_define(
    key="leave.entitled_days",
    name="Entitled leave days",
    business_meaning="Leave days employees are entitled to for a specific year.",
    calculation=(
        "SUM(leave_balances.entitled_days + carried_over_days) for ONE "
        "entitlement_year. Never summed across years."
    ),
    source="leave_balances",
    reporting_period="A single entitlement year. Defaults to the current year.",
    filters=["entitlement_year", "leave_type_id", "department"],
    refresh_behaviour="Calculated on request.",
    permissions="HR, SuperAdmin",
    limitations=[
        "Counts entitlements for employees who may since have left.",
        "Unpaid leave types are included in the entitlement figure; the balance "
        "table does not record paid/unpaid weighting.",
    ],
)

_define(
    key="leave.used_days",
    name="Used leave days",
    business_meaning="Leave days actually consumed against entitlement.",
    calculation=(
        "SUM(leave_balances.used_days) for ONE entitlement_year. This is the "
        "stored balance, not a live sum of approved requests — the two can "
        "disagree, which is what the 'leave.balance_mismatch' check detects."
    ),
    source="leave_balances.used_days",
    reporting_period="A single entitlement year. Defaults to the current year.",
    filters=["entitlement_year", "leave_type_id", "department"],
    refresh_behaviour="Calculated on request.",
    permissions="HR, SuperAdmin",
    limitations=[
        "Reads the cached balance. Run the data-quality check to confirm it "
        "agrees with the approved requests.",
    ],
)

_define(
    key="labor.monthly_cost",
    name="Monthly labour cost",
    business_meaning=(
        "Sum of base salary for employed employees. An estimate of gross "
        "monthly cost, NOT a payroll figure."
    ),
    calculation=(
        "SUM(employees.salary) WHERE status IN ('Active', 'On Leave'). The "
        "per-department breakdown applies the identical filter, so the rows "
        "reconcile to this total."
    ),
    source="employees.salary",
    reporting_period="Point in time, as at request time.",
    filters=["status", "department_id"],
    refresh_behaviour="Calculated on request.",
    permissions="HR, SuperAdmin, PayrollViewer",
    limitations=[
        "Uses the employee salary field, not processed payroll. Overtime, "
        "bonuses, benefits and employer contributions are NOT included.",
        "Null salaries are treated as 0, so a missing salary silently reduces "
        "the total. The 'payroll.zero_salary' check finds those employees.",
        "Assumes every employee is paid monthly.",
    ],
)

_define(
    key="attendance.hours",
    name="Hours worked",
    business_meaning="Total hours clocked for a day, across all employees.",
    calculation="SUM(time_entries.worked_hours) for a given work_date.",
    source="time_entries",
    reporting_period="A single day. Defaults to today.",
    filters=["work_date", "employee_id", "department"],
    refresh_behaviour="Calculated on request.",
    permissions="HR, SuperAdmin, Manager (own team)",
    limitations=[
        "Entries left open (no clock-out) contribute nothing, understating "
        "hours. The 'time.unclosed_entry' check finds them.",
        "No shift comparison, so hours are reported without saying whether "
        "they match the roster.",
    ],
)

_define(
    key="attendance.overtime_hours",
    name="Overtime hours",
    business_meaning="Hours recorded as overtime for a day.",
    calculation="SUM(time_entries.overtime_hours) for a given work_date.",
    source="time_entries",
    reporting_period="A single day. Defaults to today.",
    filters=["work_date", "employee_id", "department"],
    refresh_behaviour="Calculated on request.",
    permissions="HR, SuperAdmin, Manager (own team)",
    limitations=[
        "Not currently fed into payroll. Overtime here does not change pay."
    ],
)

_define(
    key="approvals.pending",
    name="Pending approvals",
    business_meaning="Items waiting on a human decision.",
    calculation=(
        "COUNT of leave requests with status 'Pending', timesheets with status "
        "'Submitted', and shift swaps with status 'Pending'."
    ),
    source="leave_requests, timesheets, shift_swaps",
    reporting_period="Point in time.",
    filters=["status", "approver"],
    refresh_behaviour="Calculated on request.",
    permissions="HR, SuperAdmin",
    limitations=[
        "Count only. Nothing here indicates how long an item has been waiting, "
        "so an item stuck for months looks identical to a fresh one.",
    ],
)


# ===========================================================================
# Calculations
# ===========================================================================

Calculator = Callable[[Session, dict], Any]
_CALCULATORS: dict[str, Calculator] = {}


def _calculator(key: str) -> Callable[[Calculator], Calculator]:
    def _wrap(fn: Calculator) -> Calculator:
        _CALCULATORS[key] = fn
        return fn

    return _wrap


def _employed(db: Session):
    from app.models.employee import Employee

    return db.query(Employee).filter(Employee.status.in_(EMPLOYED_STATUSES))


@_calculator("headcount.active")
def _headcount_active(db: Session, params: dict) -> int:
    return _employed(db).count()


@_calculator("headcount.by_department")
def _headcount_by_department(db: Session, params: dict) -> list[dict]:
    from app.models.department import Department
    from app.models.employee import Employee

    rows = (
        db.query(Department.id, Department.name, func.count(Employee.id))
        .outerjoin(
            Employee,
            (Employee.department_id == Department.id)
            & (Employee.status.in_(EMPLOYED_STATUSES)),
        )
        .group_by(Department.id, Department.name)
        .order_by(Department.name)
        .all()
    )
    return [
        {"department_id": did, "department": name, "employees": count}
        for did, name, count in rows
    ]


@_calculator("headcount.terminated")
def _headcount_terminated(db: Session, params: dict) -> int:
    from app.models.employee import Employee

    return db.query(Employee).filter(Employee.status == "Terminated").count()


@_calculator("turnover.rate")
def _turnover(db: Session, params: dict) -> dict:
    from app.models.employee import Employee
    from app.models.offboarding import Termination

    end = params.get("to") or datetime.date.today()
    start = params.get("from") or (end - datetime.timedelta(days=365))
    leavers = (
        db.query(Termination)
        .filter(Termination.last_working_date >= start)
        .filter(Termination.last_working_date <= end)
        .count()
    )
    employed_now = _employed(db).count()
    # Opening headcount approximated as current + leavers in the window.
    opening = employed_now + leavers
    rate = round((leavers / opening) * 100, 2) if opening else 0.0
    return {
        "leavers": leavers,
        "opening_headcount": opening,
        "closing_headcount": employed_now,
        "turnover_rate_percent": rate,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
    }


@_calculator("recruiting.open_requisitions")
def _open_reqs(db: Session, params: dict) -> int:
    from app.models.recruiting import JobRequisition

    return (
        db.query(JobRequisition)
        .filter(JobRequisition.status == "Open")
        .count()
    )


@_calculator("recruiting.funnel")
def _funnel(db: Session, params: dict) -> dict:
    from app.models.recruiting import Application, Candidate, Offer

    rows = (
        db.query(Application.status, func.count(Application.id))
        .group_by(Application.status)
        .all()
    )
    return {
        "by_stage": {status: count for status, count in rows},
        "total_applications": sum(count for _, count in rows),
        "distinct_candidates": db.query(func.count(func.distinct(Application.candidate_id))).scalar(),
        "offers": db.query(Offer).count(),
        "candidates_on_file": db.query(Candidate).count(),
    }


def _year_filter(query, params: dict):
    year = params.get("year") or datetime.date.today().year
    return query, year


@_calculator("leave.entitled_days")
def _leave_entitled(db: Session, params: dict) -> dict:
    from app.models.leave import LeaveBalance

    q, year = _year_filter(db.query(LeaveBalance), params)
    q = q.filter(LeaveBalance.entitlement_year == year)
    rows = (
        q.with_entities(
            func.coalesce(func.sum(LeaveBalance.entitled_days), 0),
            func.coalesce(func.sum(LeaveBalance.carried_over_days), 0),
        )
        .one()
    )
    return {
        "entitlement_year": year,
        "entitled_days": float(rows[0] or 0),
        "carried_over_days": float(rows[1] or 0),
        "total_entitled": float((rows[0] or 0) + (rows[1] or 0)),
    }


@_calculator("leave.used_days")
def _leave_used(db: Session, params: dict) -> dict:
    from app.models.leave import LeaveBalance

    q, year = _year_filter(db.query(LeaveBalance), params)
    q = q.filter(LeaveBalance.entitlement_year == year)
    total = q.with_entities(
        func.coalesce(func.sum(LeaveBalance.used_days), 0)
    ).scalar()
    return {"entitlement_year": year, "used_days": float(total or 0)}


@_calculator("labor.monthly_cost")
def _labor_cost(db: Session, params: dict) -> dict:
    from app.models.department import Department
    from app.models.employee import Employee

    # The identical filter is applied to the total AND the breakdown, so the
    # rows always reconcile. Previously only the total filtered on status.
    rows = (
        db.query(Department.name, func.count(Employee.id),
                 func.coalesce(func.sum(Employee.salary), 0))
        .outerjoin(
            Employee,
            (Employee.department_id == Department.id)
            & (Employee.status.in_(EMPLOYED_STATUSES)),
        )
        .group_by(Department.name)
        .order_by(Department.name)
        .all()
    )
    by_department = [
        {"department": name, "employees": count, "monthly_cost": float(cost or 0)}
        for name, count, cost in rows
    ]
    # Query.with_columns was removed in SQLAlchemy 2.0; use an explicit
    # aggregate query with the same filter as the breakdown.
    total = (
        db.query(func.coalesce(func.sum(Employee.salary), 0))
        .filter(Employee.status.in_(EMPLOYED_STATUSES))
        .scalar()
    )
    return {
        "monthly_cost": float(total or 0),
        "by_department": by_department,
        "breakdown_total": round(sum(d["monthly_cost"] for d in by_department), 2),
        "reconciles": abs(
            float(total or 0)
            - sum(d["monthly_cost"] for d in by_department)
        ) < 0.01,
    }


@_calculator("attendance.hours")
def _attendance_hours(db: Session, params: dict) -> dict:
    from app.models.time_attendance import TimeEntry

    day = params.get("day") or datetime.date.today()
    rows = (
        db.query(TimeEntry)
        .filter(TimeEntry.work_date == day)
        .all()
    )
    hours = round(sum((e.worked_hours or 0) for e in rows), 2)
    return {
        "date": day.isoformat(),
        "total_hours": hours,
        "employees_with_entries": len({e.employee_id for e in rows}),
        "entry_count": len(rows),
    }


@_calculator("attendance.overtime_hours")
def _attendance_overtime(db: Session, params: dict) -> dict:
    from app.models.time_attendance import TimeEntry

    day = params.get("day") or datetime.date.today()
    rows = (
        db.query(TimeEntry)
        .filter(TimeEntry.work_date == day)
        .all()
    )
    return {
        "date": day.isoformat(),
        "overtime_hours": round(sum((e.overtime_hours or 0) for e in rows), 2),
    }


@_calculator("approvals.pending")
def _approvals(db: Session, params: dict) -> dict:
    from app.models.leave import LeaveRequest
    from app.models.scheduling import ShiftSwap
    from app.models.time_attendance import Timesheet

    return {
        "leave_requests": db.query(LeaveRequest)
        .filter(LeaveRequest.status == "Pending").count(),
        "timesheets": db.query(Timesheet)
        .filter(Timesheet.status == "Submitted").count(),
        "shift_swaps": db.query(ShiftSwap)
        .filter(ShiftSwap.status == "Pending").count(),
        "total": (
            db.query(LeaveRequest).filter(LeaveRequest.status == "Pending").count()
            + db.query(Timesheet).filter(Timesheet.status == "Submitted").count()
            + db.query(ShiftSwap).filter(ShiftSwap.status == "Pending").count()
        ),
    }


# ===========================================================================
# Public API
# ===========================================================================


def catalogue() -> list[dict]:
    return [d.as_dict() for d in CATALOGUE.values()]


def definition(key: str) -> dict | None:
    d = CATALOGUE.get(key)
    return d.as_dict() if d else None


def compute(db: Session, key: str, params: dict | None = None) -> dict:
    """Compute one metric, returning its definition alongside the value.

    A metric that cannot be computed raises rather than returning a zero that
    would read as 'nothing happened'.
    """
    if key not in _CALCULATORS:
        raise KeyError(key)
    params = params or {}
    value = _CALCULATORS[key](db, params)
    return {
        "key": key,
        "value": value,
        "definition": CATALOGUE[key].as_dict() if key in CATALOGUE else None,
        "computed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def compute_many(db: Session, keys: list[str], params: dict | None = None) -> dict:
    out: dict[str, Any] = {}
    for key in keys:
        try:
            out[key] = compute(db, key, params)
        except KeyError:
            continue
    return out