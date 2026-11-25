"""The leave domain: types, balances, the ledger behind them, and requests.

Every change to a balance goes through the ledger
(:mod:`app.services.leave`). A balance is not a number that is edited; it is
the sum of a signed history, and the columns on the balance row are a cache
of that sum. The functions here therefore write a ledger row whenever they
move a balance, and they do it in the caller's transaction: nothing in this
module commits, so the endpoint's single commit covers the movement, the
ledger row and the audit record together.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.booleans import is_true
from app.models.employee import Employee
from app.models.leave import (
    LeaveBalance,
    LeaveLedgerEntryType,
    LeaveRequest,
    LeaveType,
)
from app.schemas.leave import (
    EntitlementCreate,
    LeaveRequestCreate,
    LeaveRequestUpdate,
    LeaveTypeCreate,
    LeaveTypeUpdate,
)
from app.services import leave as ledger


# --- Leave types ------------------------------------------------------------ #

def get_leave_type(db: Session, leave_type_id: int) -> LeaveType | None:
    return db.query(LeaveType).filter(LeaveType.id == leave_type_id).first()


def get_leave_type_by_code(db: Session, code: str) -> LeaveType | None:
    return db.query(LeaveType).filter(LeaveType.code == code).first()


def get_leave_types(db: Session, active_only: bool = False) -> list[LeaveType]:
    query = db.query(LeaveType)
    if active_only:
        query = query.filter(is_true(LeaveType.is_active))
    return query.order_by(LeaveType.code).all()


def create_leave_type(db: Session, payload: LeaveTypeCreate) -> LeaveType:
    db_obj = LeaveType(**payload.model_dump())
    db.add(db_obj)
    db.flush()
    db.refresh(db_obj)
    return db_obj


def update_leave_type(db: Session, db_obj: LeaveType, payload: LeaveTypeUpdate) -> LeaveType:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.flush()
    db.refresh(db_obj)
    return db_obj


# --- Balances / entitlements ------------------------------------------------ #

def get_balances(db: Session, employee_id: int | None = None, year: int | None = None):
    query = db.query(LeaveBalance, LeaveType.name).join(
        LeaveType, LeaveBalance.leave_type_id == LeaveType.id
    )
    if employee_id:
        query = query.filter(LeaveBalance.employee_id == employee_id)
    if year:
        query = query.filter(LeaveBalance.entitlement_year == year)
    rows = query.order_by(LeaveBalance.employee_id, LeaveBalance.leave_type_id).all()
    return [{"balance": b, "leave_type_name": name} for b, name in rows]


def get_balance(db: Session, balance_id: int) -> LeaveBalance | None:
    return db.query(LeaveBalance).filter(LeaveBalance.id == balance_id).first()


def assign_entitlements(db: Session, payload: EntitlementCreate) -> list[LeaveBalance]:
    """Give every active employee an entitlement for a leave type / year.

    Each entitlement is an ``ENTITLEMENT`` row in the ledger, written in the
    same transaction as the balance it belongs to, and the carry-over is a
    ``CARRY_OVER`` row beside it. A balance that exists without its ledger
    rows is a balance nobody can reconcile, so the two are always written
    together.
    """
    employees = db.query(Employee).filter(Employee.status == "Active").all()
    types = (
        db.query(LeaveType).filter(LeaveType.id == payload.leave_type_id).all()
        if payload.leave_type_id
        else db.query(LeaveType).filter(is_true(LeaveType.is_active)).all()
    )
    created: list[LeaveBalance] = []
    for employee in employees:
        for leave_type in types:
            existing = ledger.find_balance(
                db,
                employee.id,
                leave_type.id,
                payload.entitlement_year,
            )
            if existing:
                continue
            # Tenure-based accrual: base + 1 day per year of service (capped at +5)
            base = (
                payload.entitled_days
                if payload.entitled_days is not None
                else leave_type.max_days_per_year
            )
            tenure_years = 0
            if employee.hire_date:
                tenure_years = max(0, payload.entitlement_year - employee.hire_date.year)
            tenure_bonus = min(tenure_years, 5)
            entitled = base + (tenure_bonus if leave_type.is_paid else 0)

            balance = LeaveBalance(
                employee_id=employee.id,
                leave_type_id=leave_type.id,
                entitlement_year=payload.entitlement_year,
                entitled_days=Decimal("0"),
                carried_over_days=Decimal("0"),
                used_days=Decimal("0"),
            )
            db.add(balance)
            ledger.post_entry(
                db,
                balance,
                LeaveLedgerEntryType.ENTITLEMENT,
                entitled,
                reference_type="entitlement",
                reference_id=None,
                description=(
                    f"Entitlement for {leave_type.code} in "
                    f"{payload.entitlement_year}"
                ),
            )
            if payload.carried_over_days:
                ledger.post_entry(
                    db,
                    balance,
                    LeaveLedgerEntryType.CARRY_OVER,
                    payload.carried_over_days,
                    reference_type="carry_over",
                    reference_id=None,
                    description=(
                        f"Days carried forward into {payload.entitlement_year}"
                    ),
                )
            created.append(balance)
    if created:
        db.flush()
        for balance in created:
            db.refresh(balance)
    return created


# --- Requests --------------------------------------------------------------- #

def working_days_between(start: date, end: date) -> float:
    """Weekday count (Mon-Fri) inclusive of both ends."""
    if end < start:
        return 0
    days = 0
    day = start
    while day <= end:
        if day.weekday() < 5:
            days += 1
        day += timedelta(days=1)
    return float(days)


def get_requests(db: Session, employee_id: int | None = None, status: str | None = None):
    query = db.query(LeaveRequest, LeaveType.name).join(
        LeaveType, LeaveRequest.leave_type_id == LeaveType.id
    )
    if employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    if status:
        query = query.filter(LeaveRequest.status == status)
    return [
        {"request": r, "leave_type_name": name}
        for r, name in query.order_by(LeaveRequest.created_at.desc()).all()
    ]


def get_request(db: Session, request_id: int) -> LeaveRequest | None:
    return db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()


def pending_days(db: Session, employee_id: int, leave_type_id: int, year: int) -> float:
    rows = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.leave_type_id == leave_type_id,
            LeaveRequest.status.in_(["Pending", "Approved"]),
            LeaveRequest.start_date >= date(year, 1, 1),
            LeaveRequest.start_date <= date(year, 12, 31),
        )
        .all()
    )
    return round(sum(r.working_days for r in rows), 2)


def create_request(db: Session, payload: LeaveRequestCreate) -> LeaveRequest:
    if payload.end_date < payload.start_date:
        raise ValueError("end_date must be after start_date")
    db_obj = LeaveRequest(
        employee_id=payload.employee_id,
        leave_type_id=payload.leave_type_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        working_days=working_days_between(payload.start_date, payload.end_date),
        reason=payload.reason,
        status="Pending",
    )
    db.add(db_obj)
    db.flush()
    db.refresh(db_obj)
    return db_obj


def update_request(db: Session, db_obj: LeaveRequest, payload: LeaveRequestUpdate) -> LeaveRequest:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_obj, field, value)
    db_obj.working_days = working_days_between(db_obj.start_date, db_obj.end_date)
    db.add(db_obj)
    db.flush()
    db.refresh(db_obj)
    return db_obj


def decide_request(
    db: Session, db_obj: LeaveRequest, approved: bool, decided_by: int
) -> LeaveRequest:
    """Record a decision and move the balance exactly once.

    Guarded against re-deciding an already-decided request: the endpoint layer
    checks status, but this function must be safe on its own too, because any
    future caller would otherwise double-count the balance.

    An approval writes a ``USAGE`` row to the ledger and takes the days off
    the balance in the same transaction. Two things are refused rather than
    half-done:

    * there is no balance to record the leave against — the days would be
      taken from nobody and recorded nowhere;
    * the balance cannot cover the days — the ledger would record leave that
      was never available, and a balance cannot be overdrawn.
    """
    if db_obj.status not in ("Pending",):
        raise ValueError(
            f"Only pending requests can be decided (request {db_obj.id} is "
            f"'{db_obj.status}')"
        )

    if not approved:
        # Nothing was taken, so nothing is written to the ledger. A rejection
        # releases a reservation; there is no reservation to release here.
        db_obj.status = "Rejected"
        db_obj.decided_by = decided_by
        db_obj.decided_at = datetime.utcnow()
        db_obj.balance_applied = False
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)
        return db_obj

    days = Decimal(str(db_obj.working_days or 0))

    if days > 0:
        balance = ledger.find_balance(
            db, db_obj.employee_id, db_obj.leave_type_id, db_obj.start_date.year
        )
        if balance is None:
            raise ledger.NoLeaveBalance(
                "there is no leave balance for this employee, leave type and year"
            )

        available = ledger.derived_available_days(db, balance)
        if days > available:
            raise ledger.InsufficientLeaveBalance(
                f"the request is for {days} day(s) and the balance holds {available}"
            )

        ledger.post_entry(
            db,
            balance,
            LeaveLedgerEntryType.USAGE,
            -days,
            reference_type=ledger.REQUEST_REFERENCE,
            reference_id=db_obj.id,
            description=f"Leave taken for request {db_obj.id}",
            created_by=decided_by,
        )

    db_obj.status = "Approved"
    db_obj.decided_by = decided_by
    db_obj.decided_at = datetime.utcnow()
    db_obj.balance_applied = days > 0
    db.add(db_obj)
    db.flush()
    db.refresh(db_obj)
    return db_obj


def cancel_request(
    db: Session, db_obj: LeaveRequest, cancelled_by: int | None = None) -> LeaveRequest:
    """Cancel a request, giving the days back with a row of its own.

    The history is rows and never deletions: the usage row the approval
    wrote stays, and the cancellation is another row beside it. A request
    that was never posted to the ledger has nothing to reverse, and the
    cancellation is refused rather than inventing a movement.
    """
    if db_obj.status == "Approved":
        balance = ledger.find_balance(
            db, db_obj.employee_id, db_obj.leave_type_id, db_obj.start_date.year
        )
        if balance is None:
            raise ledger.NoLeaveBalance(
                "there is no leave balance for this employee, leave type and year"
            )
        ledger.reverse_request_usage(
            db, balance, db_obj, created_by=cancelled_by
        )
    db_obj.status = "Cancelled"
    db.add(db_obj)
    db.flush()
    db.refresh(db_obj)
    return db_obj
