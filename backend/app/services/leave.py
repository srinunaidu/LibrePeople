"""The leave ledger: every change to a leave balance is a row.

Why a ledger
------------
A leave balance used to be three numbers on a row — entitled, carried over,
used — and nothing recorded *how* the balance got there. A balance could not
be reconciled, an over-draw was invisible, and a manual correction was
indistinguishable from a grant. The ledger replaces the cached numbers with a
signed history: every accrual, entitlement, carry-over, usage, adjustment,
expiry and encashment is one row, and the balance is their sum.

    available = SUM(leave_ledger.signed_days) for the balance

The three columns on ``leave_balances`` are a *cache* of that sum, kept for
the queries that read balances in bulk. They are refreshed from the ledger
whenever a row is written, and :func:`install_guard` refuses a balance that
moves without a row to account for it.

The sign convention
-------------------
``signed_days`` is positive when days come *to* the balance and negative when
they go from it.

==================  ==========  ==========================================
entry type          sign        what it means
==================  ==========  ==========================================
``accrual``         positive    a periodic grant
``entitlement``     positive    the entitlement for the year
``carry_over``      positive    days brought forward from a previous year
``usage``           negative    approved leave taken
``expiry``          negative    days lost to a use-it-or-lose-it rule
``encashment``      negative    days converted to pay
``adjustment``      either     a manual correction
==================  ==========  ==========================================

A usage that is **reversed** — a cancelled request — is a usage row with a
positive sign that references the row it reverses. The history is never
edited and never deleted: a cancellation is another row.

The cache and the ledger
------------------------
The cache holds three numbers, so the ledger's rows are mapped onto them:

* ``entitled_days`` — the accruals, the entitlements, and the adjustments
  that add days;
* ``carried_over_days`` — the carry-overs;
* ``used_days`` — the usages, the expiries, the encashments, and the
  adjustments that remove days.

With that mapping ``entitled + carried - used`` is exactly the sum of
``signed_days``, which is what makes the cache safe to read.

Privacy
-------
The ledger is a history of a person's leave, which is more sensitive than the
balance it replaces. Two rules follow, and both are enforced here:

* **No diagnosis.** A ledger row carries days and a reference, never the
  reason for the leave. The reason stays on the leave request.
* **No free text from the request.** ``description`` is written by this
  module and describes the *movement*, not the person.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import event, func
from sqlalchemy.orm import Session

from app.models.leave import (
    LeaveBalance,
    LeaveLedger,
    LeaveLedgerEntryType,
    LeaveRequest,
    LeaveType,
)

ZERO = Decimal("0")
CENTS = Decimal("0.01")

#: The cached columns are stored at one decimal; the ledger keeps two.
CACHE_QUANTUM = Decimal("0.1")

#: How far the cache may drift from the ledger before it is a discrepancy.
TOLERANCE = Decimal("0.01")

#: The entry types that add to the entitlement bucket.
ENTITLEMENT_TYPES = (
    LeaveLedgerEntryType.ACCRUAL,
    LeaveLedgerEntryType.ENTITLEMENT,
)

#: The entry types that carry days forward from a previous year.
CARRY_OVER_TYPES = (LeaveLedgerEntryType.CARRY_OVER,)

#: The entry types that take days off the balance.
USAGE_TYPES = (
    LeaveLedgerEntryType.USAGE,
    LeaveLedgerEntryType.EXPIRY,
    LeaveLedgerEntryType.ENCASHMENT,
)

#: The sign each entry type carries. ``None`` means "either sign".
EXPECTED_SIGN: dict[LeaveLedgerEntryType, int | None] = {
    LeaveLedgerEntryType.ACCRUAL: 1,
    LeaveLedgerEntryType.ENTITLEMENT: 1,
    LeaveLedgerEntryType.CARRY_OVER: 1,
    LeaveLedgerEntryType.USAGE: -1,
    LeaveLedgerEntryType.EXPIRY: -1,
    LeaveLedgerEntryType.ENCASHMENT: -1,
    LeaveLedgerEntryType.ADJUSTMENT: None,
}

#: Where each entry type comes from, in the vocabulary of the contract.
ENTRY_SOURCE: dict[LeaveLedgerEntryType, str] = {
    LeaveLedgerEntryType.ACCRUAL: "policy",
    LeaveLedgerEntryType.ENTITLEMENT: "policy",
    LeaveLedgerEntryType.CARRY_OVER: "policy",
    LeaveLedgerEntryType.EXPIRY: "policy",
    LeaveLedgerEntryType.USAGE: "request",
    LeaveLedgerEntryType.ADJUSTMENT: "manual",
    LeaveLedgerEntryType.ENCASHMENT: "payroll",
}

#: The reference type of the row a leave request's usage is written with.
REQUEST_REFERENCE = "leave_request"

#: The reference type of the row that reverses another row.
REVERSAL_REFERENCE = "ledger_entry"


class LedgerError(RuntimeError):
    """A ledger row could not be written as asked."""


class LedgerInvariantError(LedgerError):
    """A leave balance changed without a ledger row to account for it."""


class NoLeaveBalance(LedgerError):
    """There is no balance to record the movement against."""


class InsufficientLeaveBalance(LedgerError):
    """The balance cannot cover the movement that was asked for."""


def _to_decimal(value) -> Decimal:
    """A decimal from whatever the database or the caller gave us."""
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _quantise(value: Decimal, quantum: Decimal) -> Decimal:
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


# --- Finding the balances --------------------------------------------------


def find_balance(
    db: Session, employee_id: int, leave_type_id: int, year: int
) -> LeaveBalance | None:
    """The balance of one employee, leave type and year, if there is one."""
    return (
        db.query(LeaveBalance)
        .filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.entitlement_year == year,
        )
        .first()
    )


# --- Reading the ledger ----------------------------------------------------


def ledger_rows(db: Session, balance: LeaveBalance) -> list[LeaveLedger]:
    """Every row of a balance: the committed ones and the ones staged here.

    The staged rows are included because a balance and its ledger row are
    written in the same transaction, and the cache is refreshed before the
    flush. A query that autoflushed here would fire the guard before the
    cache had been updated, so the read is made without one.
    """
    rows: list[LeaveLedger] = []
    if balance.id is not None:
        with db.no_autoflush:
            rows = list(
                db.query(LeaveLedger)
                .filter(LeaveLedger.balance_id == balance.id)
                .all()
            )
    for entry in db.new:
        if not isinstance(entry, LeaveLedger):
            continue
        if entry.balance is balance or (
            balance.id is not None and entry.balance_id == balance.id
        ):
            rows.append(entry)
    return rows


def derived_available_days(db: Session, balance: LeaveBalance) -> Decimal:
    """The balance of one balance, derived from its ledger."""
    total = ZERO
    for row in ledger_rows(db, balance):
        total += _to_decimal(row.signed_days)
    return _quantise(total, CENTS)


def derived_sums(db: Session, balance_ids: list[int]) -> dict[int, Decimal]:
    """The derived balance of every balance in the list, in one query."""
    if not balance_ids:
        return {}
    with db.no_autoflush:
        rows = (
            db.query(
                LeaveLedger.balance_id,
                func.coalesce(func.sum(LeaveLedger.signed_days), 0),
            )
            .filter(LeaveLedger.balance_id.in_(balance_ids))
            .group_by(LeaveLedger.balance_id)
            .all()
        )
    sums: dict[int, Decimal] = {
        int(balance_id): _to_decimal(total) for balance_id, total in rows
    }
    for entry in db.new:
        if isinstance(entry, LeaveLedger) and entry.balance_id in balance_ids:
            sums[entry.balance_id] = sums.get(entry.balance_id, ZERO) + _to_decimal(
                entry.signed_days
            )
    return {
        balance_id: _quantise(total, CENTS) for balance_id, total in sums.items()
    }


def buckets(rows: list[LeaveLedger]) -> tuple[Decimal, Decimal, Decimal]:
    """The three cached columns, read back out of the ledger rows."""
    entitled = carried = used = ZERO
    for row in rows:
        days = _to_decimal(row.signed_days)
        if row.entry_type in ENTITLEMENT_TYPES:
            entitled += days
        elif row.entry_type in CARRY_OVER_TYPES:
            carried += days
        elif row.entry_type in USAGE_TYPES:
            # A usage of -2 is two days used; a reversal of +2 is two days
            # given back, which is the same bucket with the other sign.
            used += -days
        else:
            # An adjustment corrects the balance: a positive one adds days
            # to the entitlement, a negative one takes days off the used
            # column.
            if days >= 0:
                entitled += days
            else:
                used += -days
    return entitled, carried, used


def refresh_cache(db: Session, balance: LeaveBalance) -> LeaveBalance:
    """Write the ledger's sum into the balance's cached columns."""
    entitled, carried, used = buckets(ledger_rows(db, balance))
    balance.entitled_days = _quantise(entitled, CACHE_QUANTUM)
    balance.carried_over_days = _quantise(carried, CACHE_QUANTUM)
    balance.used_days = _quantise(used, CACHE_QUANTUM)
    db.add(balance)
    return balance


# --- Writing the ledger ----------------------------------------------------


def _write_entry(
    db: Session,
    balance: LeaveBalance,
    entry_type: LeaveLedgerEntryType,
    signed_days,
    *,
    reference_type: str | None = None,
    reference_id: int | None = None,
    description: str | None = None,
    created_by: int | None = None,
) -> LeaveLedger:
    """Write one row to the ledger and refresh the cached balance.

    This is the one place a ledger row is created. The row and the cache are
    written together, in the caller's transaction: the caller commits, and
    the commit is what makes both of them durable. Nothing here commits, so a
    caller that rolls back leaves neither the row nor the moved balance
    behind.
    """
    days = _to_decimal(signed_days)
    entry = LeaveLedger(
        balance=balance,
        employee_id=balance.employee_id,
        leave_type_id=balance.leave_type_id,
        entitlement_year=balance.entitlement_year,
        entry_type=entry_type,
        signed_days=days,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        created_by=created_by,
    )
    db.add(entry)
    refresh_cache(db, balance)
    return entry


def post_entry(
    db: Session,
    balance: LeaveBalance,
    entry_type: LeaveLedgerEntryType,
    signed_days,
    *,
    reference_type: str | None = None,
    reference_id: int | None = None,
    description: str | None = None,
    created_by: int | None = None,
) -> LeaveLedger:
    """Write one movement to the ledger and refresh the cached balance.

    The sign of the movement is checked against the entry type, so a usage
    cannot be written as a grant by mistake. A *reversal* — a usage with the
    other sign — goes through :func:`reverse_entry` instead.
    """
    days = _to_decimal(signed_days)
    if days == 0:
        raise LedgerError("a ledger row of zero days records nothing")
    expected = EXPECTED_SIGN.get(entry_type)
    if expected is not None and (days > 0) != (expected > 0):
        raise LedgerError(
            f"a {entry_type.value} entry is "
            f"{'positive' if expected > 0 else 'negative'}"
        )
    return _write_entry(
        db,
        balance,
        entry_type,
        days,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        created_by=created_by,
    )


def request_usage(db: Session, request: LeaveRequest) -> LeaveLedger | None:
    """The usage row a leave request's approval wrote, if it wrote one."""
    rows = (
        db.query(LeaveLedger)
        .filter(
            LeaveLedger.entry_type == LeaveLedgerEntryType.USAGE,
            LeaveLedger.reference_type == REQUEST_REFERENCE,
            LeaveLedger.reference_id == request.id,
        )
        .all()
    )
    taken = [row for row in rows if _to_decimal(row.signed_days) < 0]
    if not taken:
        return None
    return sorted(taken, key=lambda row: row.id or 0)[-1]


def request_reversals(db: Session, request: LeaveRequest) -> list[LeaveLedger]:
    """The rows that gave a leave request's usage back."""
    return (
        db.query(LeaveLedger)
        .filter(
            LeaveLedger.entry_type == LeaveLedgerEntryType.USAGE,
            LeaveLedger.reference_type == REQUEST_REFERENCE,
            LeaveLedger.reference_id == request.id,
            LeaveLedger.signed_days > 0,
        )
        .all()
    )


def reverse_request_usage(
    db: Session,
    balance: LeaveBalance,
    request: LeaveRequest,
    *,
    created_by: int | None = None,
) -> LeaveLedger:
    """Give a leave request's leave back, with a row of its own.

    A cancellation without a usage to reverse is refused: there is nothing
    to give back, and writing a row anyway would invent leave that was never
    taken.
    """
    usage = request_usage(db, request)
    if usage is None:
        raise LedgerError(
            "there is no usage to reverse: the request was never posted"
        )
    outstanding = outstanding_usage_days(db, request)
    if outstanding <= 0:
        raise LedgerError("the usage has already been reversed")
    return _write_entry(
        db,
        balance,
        LeaveLedgerEntryType.USAGE,
        outstanding,
        reference_type=REQUEST_REFERENCE,
        reference_id=request.id,
        description=(
            f"Reversal of the leave taken for request {request.id}"
        ),
        created_by=created_by,
    )


def outstanding_usage_days(db: Session, request: LeaveRequest) -> Decimal:
    """How many days of a leave request are still on the balance."""
    usage = request_usage(db, request)
    if usage is None:
        return ZERO
    reversals = sum(
        (_to_decimal(row.signed_days) for row in request_reversals(db, request)),
        ZERO,
    )
    return _quantise(-_to_decimal(usage.signed_days) - reversals, CENTS)


# --- The guard -------------------------------------------------------------


def _guard(session, flush_context, instances) -> None:
    """Refuse a balance that moved without a ledger row to account for it.

    This is what makes "every balance change writes a row" a property of the
    system rather than a habit: a balance that is changed without a row is
    not flushed, so neither the change nor the row is written.
    """
    for obj in session.dirty:
        if not isinstance(obj, LeaveBalance):
            continue
        expected = derived_available_days(session, obj)
        actual = _to_decimal(obj.available_days)
        if abs(expected - actual) > TOLERANCE:
            raise LedgerInvariantError(
                "a leave balance changed without a ledger row to account for it "
                f"(balance {obj.id}: cached {actual}, ledger {expected})"
            )


def install_guard() -> None:
    """Install the guard once per process."""
    from sqlalchemy.orm import Session as OrmSession

    if getattr(OrmSession, "_karmathy_leave_ledger_guard", False):
        return
    event.listen(OrmSession, "before_flush", _guard)
    OrmSession._karmathy_leave_ledger_guard = True


install_guard()


# --- The reconciliation ----------------------------------------------------

#: The state of a balance against its ledger.
IN_SYNC = "in_sync"
OUT_OF_SYNC = "out_of_sync"
NO_LEDGER = "no_ledger"


def reconcile(
    db: Session,
    *,
    employee_ids: set[int] | None = None,
    year: int | None = None,
) -> list[dict]:
    """Every balance against its ledger, with the difference between them.

    The report is about people, so it is scoped by the caller before it
    reaches this function, and it carries no description and no reason: only
    the numbers that disagree.
    """
    query = db.query(LeaveBalance, LeaveType.name).join(
        LeaveType, LeaveBalance.leave_type_id == LeaveType.id
    )
    if employee_ids is not None:
        if not employee_ids:
            return []
        query = query.filter(LeaveBalance.employee_id.in_(employee_ids))
    if year is not None:
        query = query.filter(LeaveBalance.entitlement_year == year)

    balances = query.order_by(
        LeaveBalance.employee_id, LeaveBalance.leave_type_id
    ).all()

    rows: list[dict] = []
    for balance, leave_type_name in balances:
        entries = ledger_rows(db, balance)
        derived = _quantise(
            sum((_to_decimal(row.signed_days) for row in entries), ZERO), CENTS
        )
        cached = _to_decimal(balance.available_days)
        difference = _quantise(derived - cached, CENTS)
        if not entries:
            state = NO_LEDGER
        elif abs(difference) > TOLERANCE:
            state = OUT_OF_SYNC
        else:
            state = IN_SYNC
        rows.append(
            {
                "balance_id": balance.id,
                "employee_id": balance.employee_id,
                "leave_type_id": balance.leave_type_id,
                "leave_type_name": leave_type_name,
                "entitlement_year": balance.entitlement_year,
                "cached_entitled_days": float(_to_decimal(balance.entitled_days)),
                "cached_carried_over_days": float(
                    _to_decimal(balance.carried_over_days)
                ),
                "cached_used_days": float(_to_decimal(balance.used_days)),
                "cached_available_days": float(cached),
                "ledger_available_days": float(derived),
                "difference_days": float(difference),
                "ledger_entries": len(entries),
                "state": state,
            }
        )
    return rows


# --- The payroll handoff ---------------------------------------------------


def working_days_between(start: date, end: date) -> int:
    """The weekdays between two dates, both ends included."""
    if end < start:
        return 0
    days = 0
    day = start
    while day <= end:
        if day.weekday() < 5:
            days += 1
        day = date.fromordinal(day.toordinal() + 1)
    return days


def approved_leave_for_period(
    db: Session, period_start: date, period_end: date
) -> list[dict]:
    """The approved leave that falls in a period, quantified.

    This is the half of ``LV-05`` that the leave lane owns: the approved
    leave of the period, with the quantity and the period it belongs to, in
    the shape the payroll lane consumes it in.

    The quantity is the leave that falls *inside* the period: a request that
    starts in one month and ends in the next is split between them, so a pay
    run never takes the whole of it.
    """
    if period_end < period_start:
        return []

    requests = (
        db.query(LeaveRequest, LeaveType.code, LeaveType.is_paid)
        .join(LeaveType, LeaveRequest.leave_type_id == LeaveType.id)
        .filter(LeaveRequest.status == "Approved")
        .filter(LeaveRequest.start_date <= period_end)
        .filter(LeaveRequest.end_date >= period_start)
        .order_by(LeaveRequest.employee_id, LeaveRequest.start_date)
        .all()
    )

    entries: list[dict] = []
    for request, leave_type_code, is_paid in requests:
        window_start = max(request.start_date, period_start)
        window_end = min(request.end_date, period_end)
        quantity = working_days_between(window_start, window_end)
        if quantity == 0:
            continue
        entries.append(
            {
                "employee_id": request.employee_id,
                "leave_type_id": request.leave_type_id,
                "leave_type_code": leave_type_code,
                "is_paid": bool(is_paid),
                "leave_request_id": request.id,
                "start_date": window_start,
                "end_date": window_end,
                "quantity_days": float(quantity),
            }
        )
    return entries


def ledger_view(rows: list[LeaveLedger]) -> list[dict]:
    """The rows of a balance, with the running balance after each of them.

    The running balance is what makes the ledger readable on its own: the
    sum of the rows up to that point is the balance at that point.
    """
    running = ZERO
    out: list[dict] = []
    for row in sorted(rows, key=lambda item: item.id or 0):
        days = _to_decimal(row.signed_days)
        running += days
        out.append(
            {
                "id": row.id,
                "balance_id": row.balance_id,
                "employee_id": row.employee_id,
                "leave_type_id": row.leave_type_id,
                "entitlement_year": row.entitlement_year,
                "entry_type": row.entry_type.value,
                "signed_days": float(days),
                "reference_type": row.reference_type,
                "reference_id": row.reference_id,
                "description": row.description,
                "created_at": row.created_at,
                "running_balance": float(_quantise(running, CENTS)),
                "source": ENTRY_SOURCE.get(row.entry_type, "manual"),
            }
        )
    return out
