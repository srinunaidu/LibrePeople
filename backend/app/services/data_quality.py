"""Data-quality checks.

The mission asks for a capability that detects duplicate employees, missing
required information, invalid dates, conflicting assignments, incomplete
onboarding, expiring documents, unresolved attendance exceptions, inconsistent
leave balances, missing payroll inputs, failed integrations and incomplete
migration jobs — each with severity, affected record, explanation, source,
owner, recommended correction and status.

Design
------
Checks are registered functions rather than one hand-written report, so adding
a rule does not mean editing a query. Every check returns ``Issue`` objects and
never mutates data: the brief is explicit that sensitive records must not be
silently altered, and remediation must be a deliberate, audited action.

Severity
--------
``critical``  wrong money, or records that will corrupt downstream processing
``warning``   a real gap that needs attention but is not breaking anything
``info``      worth surfacing, no action required

Every check declares a stable ``code`` so a finding can be tracked, muted or
escalated without string-matching prose.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from sqlalchemy.orm import Session

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


@dataclass
class Issue:
    code: str
    severity: str
    title: str
    entity_type: str
    entity_id: int | None
    explanation: str
    source: str
    owner_role: str
    recommendation: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "title": self.title,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "explanation": self.explanation,
            "source": self.source,
            "owner_role": self.owner_role,
            "recommendation": self.recommendation,
            "details": self.details,
        }


Check = Callable[[Session], Iterable[Issue]]

_REGISTRY: dict[str, Check] = {}


def register(code: str) -> Callable[[Check], Check]:
    def _wrap(fn: Check) -> Check:
        _REGISTRY[code] = fn
        return fn

    return _wrap


def run_all(db: Session) -> list[Issue]:
    """Run every registered check and return issues worst-first.

    A check that raises is reported as a single issue rather than aborting the
    sweep — one broken rule must not hide the other twenty.
    """
    issues: list[Issue] = []
    for code, check in _REGISTRY.items():
        try:
            issues.extend(check(db))
        except Exception as exc:  # noqa: BLE001
            issues.append(
                Issue(
                    code=f"{code}.check_failed",
                    severity="warning",
                    title=f"Data-quality check '{code}' could not run",
                    entity_type="System",
                    entity_id=None,
                    explanation=(
                        "The check raised an error, so its findings are missing "
                        "from this report. Treat the absence as unknown, not as "
                        "'no problems'."
                    ),
                    source=code,
                    owner_role="PlatformAdmin",
                    recommendation="Check the application logs for this check.",
                    details={"error_type": type(exc).__name__},
                )
            )
    issues.sort(key=lambda i: (SEVERITY_ORDER.get(i.severity, 9), i.code))
    return issues


def summarise(issues: list[Issue]) -> dict:
    by_severity: dict[str, int] = {}
    by_code: dict[str, int] = {}
    for i in issues:
        by_severity[i.severity] = by_severity.get(i.severity, 0) + 1
        by_code[i.code] = by_code.get(i.code, 0) + 1
    return {
        "total": len(issues),
        "by_severity": by_severity,
        "by_code": by_code,
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


# ===========================================================================
# Employee record integrity
# ===========================================================================


@register("employee.duplicate_email")
def check_duplicate_email(db: Session) -> Iterable[Issue]:
    """Emails that differ only by case or surrounding whitespace.

    `employees.email` already carries a UNIQUE constraint, so an exact duplicate
    cannot be inserted — that is why this rule normalises first. Case-sensitive
    uniqueness still permits `Ann@x.com` and `ann@x.com`, or a value with a
    trailing space, to coexist. Both defeat single sign-on and payroll exports,
    which key off email.
    """
    from app.models.employee import Employee

    rows = (
        db.query(Employee.id, Employee.employee_id, Employee.email)
        .filter(Employee.email.isnot(None))
        .all()
    )
    groups: dict[str, list] = {}
    for emp_id, code, email in rows:
        if not email:
            continue
        groups.setdefault(email.strip().lower(), []).append((emp_id, code, email))

    for normalised, members in groups.items():
        if len(members) < 2:
            continue
        distinct = {m[2] for m in members}
        yield Issue(
            code="employee.duplicate_email",
            severity="critical",
            title=f"{len(members)} employee records share the email "
                  f"'{normalised}' once case and whitespace are ignored",
            entity_type="Employee",
            entity_id=members[0][0],
            explanation=(
                f"{len(members)} records resolve to the same email when "
                f"normalised. The UNIQUE constraint does not catch case or "
                f"whitespace differences, so these records can be merged or "
                f"blocked incorrectly by single sign-on and payroll exports."
            ),
            source="employees.email, normalised with strip().lower()",
            owner_role="HR",
            recommendation=(
                "Standardise to one address and correct the others, then "
                "re-run this check."
            ),
            details={"normalised_email": normalised,
                     "employee_ids": [m[0] for m in members],
                     "employee_codes": [m[1] for m in members],
                     "distinct_spellings": sorted(distinct)},
        )


@register("employee.missing_contact")
def check_missing_contact(db: Session) -> Iterable[Issue]:
    """Active employees with no phone number recorded."""
    from app.models.employee import Employee

    rows = (
        db.query(Employee.id, Employee.employee_id)
        .filter(Employee.status == "Active")
        .filter((Employee.phone.is_(None)) | (Employee.phone == ""))
        .limit(200)
        .all()
    )
    for emp_id, code in rows:
        yield Issue(
            code="employee.missing_contact",
            severity="info",
            title=f"No phone number recorded for {code}",
            entity_type="Employee",
            entity_id=emp_id,
            explanation=(
                "An active employee has no phone number, which limits emergency "
                "contact reachability."
            ),
            source="employees.phone",
            owner_role="HR",
            recommendation="Collect the number during the next profile review.",
            details={"employee_code": code},
        )


@register("employee.invalid_dates")
def check_invalid_dates(db: Session) -> Iterable[Issue]:
    """Hire dates in the future, or terminations that precede the hire date."""
    from app.models.employee import Employee
    from app.models.offboarding import Termination

    today = datetime.date.today()

    for emp_id, code, hire_date in (
        db.query(Employee.id, Employee.employee_id, Employee.hire_date)
        .filter(Employee.hire_date > today)
        .limit(100)
        .all()
    ):
        yield Issue(
            code="employee.future_hire_date",
            severity="warning",
            title=f"Hire date in the future for {code}",
            entity_type="Employee",
            entity_id=emp_id,
            explanation=(
                f"Hire date {hire_date} is after today ({today}). The employee "
                "will not be eligible for payroll or benefits until then, but "
                "may be over-counted in headcount."
            ),
            source="employees.hire_date",
            owner_role="HR",
            recommendation="Confirm the start date, or set status to 'Onboarding'.",
            details={"employee_code": code, "hire_date": str(hire_date)},
        )

    for t_id, emp_id, last_working, hire_date in (
        db.query(Termination.id, Termination.employee_id,
                 Termination.last_working_date, Employee.hire_date)
        .join(Employee, Employee.id == Termination.employee_id)
        .all()
    ):
        if hire_date and last_working and last_working < hire_date:
            yield Issue(
                code="employee.termination_before_hire",
                severity="critical",
                title="Termination date precedes the hire date",
                entity_type="Termination",
                entity_id=t_id,
                explanation=(
                    f"Last working date {last_working} is before the employee's "
                    f"hire date {hire_date}. Final pay and service-length "
                    "calculations built on this would be wrong."
                ),
                source="offboarding.terminations + employees.hire_date",
                owner_role="HR",
                recommendation="Correct one of the two dates before finalising payroll.",
                details={"employee_id": emp_id,
                         "last_working_date": str(last_working),
                         "hire_date": str(hire_date)},
            )


@register("employee.conflicting_assignment")
def check_conflicting_assignment(db: Session) -> Iterable[Issue]:
    """An employee whose job belongs to a different department.

    This is the classic org-data inconsistency: the employee appears in
    Department A while their Job is anchored to Department B, so department
    headcount and reporting disagree.
    """
    from app.models.employee import Employee
    from app.models.job import Job

    rows = (
        db.query(Employee.id, Employee.employee_id, Employee.department_id,
                 Job.department_id, Job.title)
        .join(Job, Job.id == Employee.job_id)
        .filter(Job.department_id.isnot(None))
        .filter(Job.department_id != Employee.department_id)
        .limit(200)
        .all()
    )
    for emp_id, code, emp_dept, job_dept, title in rows:
        yield Issue(
            code="employee.department_job_mismatch",
            severity="warning",
            title=f"{code}: employee and job are in different departments",
            entity_type="Employee",
            entity_id=emp_id,
            explanation=(
                f"The employee is in department {emp_dept} but their job "
                f"'{title}' belongs to department {job_dept}. Department "
                "headcount and reporting will disagree depending on which is used."
            ),
            source="employees.department_id vs jobs.department_id",
            owner_role="HR",
            recommendation=(
                "Move the employee to the job's department, or move the job."
            ),
            details={"employee_code": code, "employee_department_id": emp_dept,
                     "job_department_id": job_dept, "job_title": title},
        )


@register("employee.manager_cycle")
def check_manager_cycle(db: Session) -> Iterable[Issue]:
    """A reporting chain that loops (A manages B manages A).

    Left uncorrected this makes any recursive manager query infinite.
    """
    from app.models.employee import Employee

    rows = db.query(Employee.id, Employee.employee_id, Employee.manager_id).all()
    manager_of = {r[0]: r[2] for r in rows}
    code_of = {r[0]: r[1] for r in rows}

    for emp_id in manager_of:
        seen: set[int] = set()
        cur = manager_of.get(emp_id)
        while cur is not None and cur in manager_of:
            if cur in seen:
                yield Issue(
                    code="employee.manager_cycle",
                    severity="critical",
                    title=f"Reporting cycle involving {code_of.get(emp_id)}",
                    entity_type="Employee",
                    entity_id=emp_id,
                    explanation=(
                        "This employee's management chain loops back on itself. "
                        "Any recursive query over reporting lines will not "
                        "terminate."
                    ),
                    source="employees.manager_id",
                    owner_role="HR",
                    recommendation="Break the loop by clearing or correcting manager_id.",
                    details={"employee_code": code_of.get(emp_id),
                             "cycle_at_employee_id": cur},
                )
                break
            seen.add(cur)
            cur = manager_of.get(cur)


# ===========================================================================
# Leave
# ===========================================================================


@register("leave.balance_overdrawn")
def check_leave_overdrawn(db: Session) -> Iterable[Issue]:
    """Used leave exceeding the entitlement plus carryover."""
    from app.models.leave import LeaveBalance

    rows = (
        db.query(LeaveBalance.id, LeaveBalance.employee_id,
                 LeaveBalance.entitled_days, LeaveBalance.carried_over_days,
                 LeaveBalance.used_days)
        .all()
    )
    for bal_id, emp_id, entitled, carried, used in rows:
        capacity = (entitled or 0) + (carried or 0)
        if (used or 0) > capacity:
            yield Issue(
                code="leave.balance_overdrawn",
                severity="critical",
                title="Leave taken exceeds the entitlement",
                entity_type="LeaveBalance",
                entity_id=bal_id,
                explanation=(
                    f"{used} day(s) used against a {capacity} day entitlement "
                    f"({entitled} + {carried} carryover). Payroll and absence "
                    "reporting will overstate the balance."
                ),
                source="leave_balances.used_days vs entitled + carried_over",
                owner_role="HR",
                recommendation=(
                    "Approve an exception, or adjust the entitlement. Do not "
                    "edit used_days directly — reconcile against the requests."
                ),
                details={"employee_id": emp_id, "entitled_days": entitled,
                         "carried_over_days": carried, "used_days": used},
            )


@register("leave.balance_mismatch")
def check_leave_balance_mismatch(db: Session) -> Iterable[Issue]:
    """Stored used_days disagreeing with the sum of approved requests.

    This is the reconciliation the mission asks for: the balance is a cached
    figure and the requests are the source of truth.
    """
    from app.models.leave import LeaveBalance, LeaveRequest

    balances = (
        db.query(LeaveBalance.id, LeaveBalance.employee_id,
                 LeaveBalance.leave_type_id, LeaveBalance.entitlement_year,
                 LeaveBalance.used_days)
        .all()
    )
    for bal_id, emp_id, type_id, year, used in balances:
        approved = (
            db.query(LeaveRequest.working_days)
            .filter(LeaveRequest.employee_id == emp_id)
            .filter(LeaveRequest.leave_type_id == type_id)
            .filter(LeaveRequest.status == "Approved")
            .filter(LeaveRequest.start_date >= datetime.date(year, 1, 1))
            .filter(LeaveRequest.start_date <= datetime.date(year, 12, 31))
            .all()
        )
        expected = round(sum((r[0] or 0) for r in approved), 2)
        if abs((used or 0) - expected) > 0.01:
            yield Issue(
                code="leave.balance_mismatch",
                severity="critical",
                title="Leave balance does not match approved requests",
                entity_type="LeaveBalance",
                entity_id=bal_id,
                explanation=(
                    f"Balance shows {used} day(s) used but approved requests for "
                    f"{year} total {expected}. One of the two is wrong, so "
                    "absence reporting cannot be trusted."
                ),
                source="leave_balances vs approved leave_requests",
                owner_role="HR",
                recommendation=(
                    "Reconcile against the approved requests, then correct the "
                    "balance through the request workflow rather than directly."
                ),
                details={"employee_id": emp_id, "leave_type_id": type_id,
                         "entitlement_year": year, "balance_used_days": used,
                         "requests_total_days": expected},
            )


# ===========================================================================
# Payroll
# ===========================================================================


@register("payroll.active_without_profile")
def check_payroll_missing_profile(db: Session) -> Iterable[Issue]:
    """Active employees who will be silently skipped by the next pay run."""
    from app.models.employee import Employee
    from app.models.payroll import EmployeePayProfile

    profiled = {
        r[0] for r in db.query(EmployeePayProfile.employee_id).all()
    }
    rows = (
        db.query(Employee.id, Employee.employee_id)
        .filter(Employee.status.in_(("Active", "On Leave")))
        .all()
    )
    for emp_id, code in rows:
        if emp_id not in profiled:
            yield Issue(
                code="payroll.active_without_profile",
                severity="critical",
                title=f"{code} will not be paid",
                entity_type="Employee",
                entity_id=emp_id,
                explanation=(
                    "This employee is active but has no pay profile, so payroll "
                    "processing excludes them without an obvious error. They "
                    "would simply not be paid."
                ),
                source="employees vs employee_pay_profiles",
                owner_role="PayrollAdmin",
                recommendation="Create a pay profile before the next pay run.",
                details={"employee_code": code},
            )


@register("payroll.zero_salary")
def check_payroll_zero_salary(db: Session) -> Iterable[Issue]:
    """Pay profiles with a zero or missing salary."""
    from app.models.payroll import EmployeePayProfile

    rows = (
        db.query(EmployeePayProfile.id, EmployeePayProfile.employee_id,
                 EmployeePayProfile.base_salary)
        .filter(
            (EmployeePayProfile.base_salary.is_(None))
            | (EmployeePayProfile.base_salary == 0)
        )
        .all()
    )
    for prof_id, emp_id, salary in rows:
        yield Issue(
            code="payroll.zero_salary",
            severity="critical",
            title="Pay profile has no salary",
            entity_type="EmployeePayProfile",
            entity_id=prof_id,
            explanation=(
                "This pay profile would produce a zero-value payslip. If it is "
                "an unpaid or part-paid arrangement it should be modelled "
                "explicitly, not left as a silent zero."
            ),
            source="employee_pay_profiles.base_salary",
            owner_role="PayrollAdmin",
            recommendation="Confirm the intended pay and set base_salary.",
            details={"employee_id": emp_id, "base_salary": salary},
        )


@register("payroll.payslip_arithmetic")
def check_payslip_arithmetic(db: Session) -> Iterable[Issue]:
    """Payslips where gross - deductions != net.

    A rounding or regression bug in the calculation engine would show up here
    before it reaches an employee.
    """
    from app.models.payroll import PaySlip

    rows = (
        db.query(PaySlip.id, PaySlip.employee_id, PaySlip.gross_pay,
                 PaySlip.total_deductions, PaySlip.net_pay)
        .all()
    )
    for slip_id, emp_id, gross, deductions, net in rows:
        expected = round((gross or 0) - (deductions or 0), 2)
        if abs((net or 0) - expected) > 0.01:
            yield Issue(
                code="payroll.payslip_arithmetic",
                severity="critical",
                title="Payslip does not balance",
                entity_type="PaySlip",
                entity_id=slip_id,
                explanation=(
                    f"Gross {gross} less deductions {deductions} should equal "
                    f"{expected}, but net is {net}. An employee would be paid "
                    "the wrong amount."
                ),
                source="pay_slips arithmetic",
                owner_role="PayrollAdmin",
                recommendation="Recalculate the run; do not hand-edit a payslip.",
                details={"employee_id": emp_id, "gross_pay": gross,
                         "total_deductions": deductions, "net_pay": net},
            )


# ===========================================================================
# Onboarding & documents
# ===========================================================================


@register("onboarding.incomplete")
def check_incomplete_onboarding(db: Session) -> Iterable[Issue]:
    """New hires whose required onboarding tasks are still open."""
    from app.models.employee import Employee
    from app.models.onboarding import OnboardingTask

    cutoff = datetime.date.today() - datetime.timedelta(days=14)
    recent = (
        db.query(Employee.id, Employee.employee_id)
        .filter(Employee.hire_date >= cutoff)
        .filter(Employee.status == "Active")
        .all()
    )
    for emp_id, code in recent:
        open_tasks = (
            db.query(OnboardingTask.id)
            .filter(OnboardingTask.employee_id == emp_id)
            .filter(OnboardingTask.status != "Completed")
            .all()
        )
        if not open_tasks:
            # No checklist at all is also a gap worth reporting once.
            any_tasks = (
                db.query(OnboardingTask.id)
                .filter(OnboardingTask.employee_id == emp_id)
                .all()
            )
            if any_tasks:
                continue
            yield Issue(
                code="onboarding.no_checklist",
                severity="warning",
                title=f"No onboarding checklist for {code}",
                entity_type="Employee",
                entity_id=emp_id,
                explanation=(
                    "This employee started in the last two weeks but has no "
                    "onboarding tasks, so required steps may have been skipped."
                ),
                source="onboarding_tasks vs employees.hire_date",
                owner_role="HR",
                recommendation="Apply the standard onboarding checklist.",
                details={"employee_code": code},
            )
        elif len(open_tasks) > 0:
            yield Issue(
                code="onboarding.incomplete",
                severity="warning",
                title=f"{len(open_tasks)} onboarding task(s) still open for {code}",
                entity_type="Employee",
                entity_id=emp_id,
                explanation=(
                    f"{code} started over two weeks ago with "
                    f"{len(open_tasks)} task(s) still incomplete."
                ),
                source="onboarding_tasks.status",
                owner_role="HR",
                recommendation="Complete or explicitly waive the outstanding tasks.",
                details={"employee_code": code,
                         "open_task_count": len(open_tasks)},
            )


@register("documents.expiring")
def check_expiring_documents(db: Session) -> Iterable[Issue]:
    """Documents expiring within 60 days, or already expired."""
    from app.models.core_hr import EmployeeDocument

    soon = datetime.date.today() + datetime.timedelta(days=60)
    rows = (
        db.query(EmployeeDocument.id, EmployeeDocument.employee_id,
                 EmployeeDocument.document_type, EmployeeDocument.expiry_date)
        .filter(EmployeeDocument.expiry_date.isnot(None))
        .filter(EmployeeDocument.expiry_date <= soon)
        .limit(200)
        .all()
    )
    today = datetime.date.today()
    for doc_id, emp_id, dtype, expiry in rows:
        expired = expiry < today
        yield Issue(
            code="document.expired" if expired else "document.expiring_soon",
            severity="critical" if expired else "warning",
            title=f"{dtype} {'has expired' if expired else 'expires soon'}",
            entity_type="EmployeeDocument",
            entity_id=doc_id,
            explanation=(
                f"This document {'expired' if expired else 'expires'} on "
                f"{expiry}. Work authorisation tied to it may no longer be valid."
            ),
            source="core_hr.employee_documents.expiry_date",
            owner_role="HR",
            recommendation="Request a renewed document from the employee.",
            details={"employee_id": emp_id, "document_type": dtype,
                     "expiry_date": str(expiry)},
        )


# ===========================================================================
# Time & attendance
# ===========================================================================


@register("time.unclosed_entry")
def check_unclosed_time_entries(db: Session) -> Iterable[Issue]:
    """Clock-ins with no matching clock-out, left open for over a day."""
    from app.models.time_attendance import TimeEntry

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    rows = (
        db.query(TimeEntry.id, TimeEntry.employee_id, TimeEntry.clock_in)
        .filter(TimeEntry.clock_out.is_(None))
        .all()
    )
    for entry_id, emp_id, clock_in in rows:
        ref = clock_in if clock_in else cutoff
        try:
            ref_aware = ref.replace(tzinfo=datetime.timezone.utc) if ref.tzinfo is None else ref
        except Exception:  # noqa: BLE001
            continue
        if ref_aware < cutoff:
            yield Issue(
                code="time.unclosed_entry",
                severity="warning",
                title="Time entry left open for more than a day",
                entity_type="TimeEntry",
                entity_id=entry_id,
                explanation=(
                    "A clock-in has no matching clock-out after more than 24 "
                    "hours. Hours worked will be understated and the employee "
                    "may be unpaid for real work."
                ),
                source="time_entries.clock_out IS NULL",
                owner_role="Manager",
                recommendation="Confirm the true end time and close the entry.",
                details={"employee_id": emp_id,
                         "clock_in": str(clock_in)},
            )


# ===========================================================================
# Registries
# ===========================================================================


def registered_codes() -> list[str]:
    return sorted(_REGISTRY)