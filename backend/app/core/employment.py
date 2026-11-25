"""The employment lifecycle and its effective-dated history.

The employee record carries a status, but until now nothing said which
statuses may follow which. An operator could move a terminated employee
straight back to `Active`, and the move left no trace, so "when did this
person leave and when were they rehired?" had no answer.

This module states the transitions once and records every change:

* ``Active``     → ``On Leave``, ``Terminated``
* ``On Leave``   → ``Active``, ``Terminated``
* ``Terminated`` → ``Rehired`` (not ``Active``: the rehire is the event)
* ``Rehired``    → ``Active``, ``On Leave``, ``Terminated``

A value that does not move (the same status again) is a no-op, not an error.
A stored status outside this vocabulary (a row written by an import or an
older release) may be corrected to any known status — refusing would leave the
bad row unfixable.

Effective dating
----------------
A change is dated. **A future date is refused**: the deployment has no
scheduler to apply a planned change, so accepting one would make the record
claim a state that has not happened. A date today or in the past is a
correction and applies now. When a change lands, the previous open history row
for that field is closed with ``effective_to`` equal to the new
``effective_from`` (exclusive), and the new row is appended. Nothing is
overwritten.

The record's current columns always show the state in force today. The history
is the evidence for how it got there.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import conflict, validation
from app.models.employee import Employee, EmployeeHistory

#: The lifecycle the deployment enforces.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "Active": frozenset({"On Leave", "Terminated"}),
    "On Leave": frozenset({"Active", "Terminated"}),
    "Terminated": frozenset({"Rehired"}),
    "Rehired": frozenset({"Active", "On Leave", "Terminated"}),
}

EMPLOYMENT_STATUSES = tuple(ALLOWED_TRANSITIONS)

#: Fields whose change is written to the effective-dated history. Name,
#: email and phone are corrections of the person's contact details, not
#: employment history; they are audited, not dated.
DATED_FIELDS = (
    "status",
    "employment_type",
    "termination_date",
    "job_id",
    "department_id",
    "manager_id",
    "salary",
)


def ensure_transition(current: str, new: str) -> None:
    """Refuse a lifecycle move the state machine does not define.

    A no-op and a correction from an unknown stored value are allowed; the
    latter so a bad import can be fixed.
    """
    if current == new:
        return
    allowed = ALLOWED_TRANSITIONS.get(current)
    if allowed is None:
        return
    if new not in allowed:
        raise conflict(
            "invalid_state_transition",
            (
                f"An employee cannot move from {current!r} to {new!r}. "
                f"From {current!r} the allowed next states are "
                f"{', '.join(sorted(allowed))}."
            ),
            current=current,
            requested=new,
            allowed=sorted(allowed),
        )


def ensure_effective_date(effective_from: date | None) -> date:
    """Default to today; refuse a date the deployment cannot yet honour."""
    today = date.today()
    if effective_from is None:
        return today
    if effective_from > today:
        raise validation(
            "validation_error",
            "A change cannot take effect in the future yet: the deployment has "
            "no scheduler to apply a planned change, and recording one would "
            "claim a state that has not happened.",
            effective_from=effective_from.isoformat(),
            today=today.isoformat(),
        )
    return effective_from


def _close_open_row(
    db: Session, employee_id: int, field: str, effective_from: date
) -> None:
    """Close the open row for this field on the day the new value starts."""
    open_row = (
        db.query(EmployeeHistory)
        .filter(
            EmployeeHistory.employee_id == employee_id,
            EmployeeHistory.field == field,
            EmployeeHistory.effective_to.is_(None),
        )
        .order_by(EmployeeHistory.effective_from.desc(), EmployeeHistory.id.desc())
        .first()
    )
    if open_row is not None:
        open_row.effective_to = effective_from


def _normalise(value: object) -> str | None:
    """A stable text form, so 1000.0 and Decimal('1000.00') are one value."""
    if value is None:
        return None
    # Amounts keep two decimals; ids and other integers stay integers. A
    # history row for `job_id` must read "1 -> 2", not "1.00 -> 2.00".
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def record_change(
    db: Session,
    employee: Employee,
    field: str,
    previous: object,
    new: object,
    *,
    effective_from: date,
    reason: str | None,
    changed_by: str | None,
) -> EmployeeHistory | None:
    """Append one history row, closing the previous row for the field.

    Returns the row, or ``None`` when the value did not change (a no-op is
    not history).
    """
    previous_text = _normalise(previous)
    new_text = _normalise(new)
    if previous_text == new_text:
        return None
    _close_open_row(db, employee.id, field, effective_from)
    row = EmployeeHistory(
        employee_id=employee.id,
        field=field,
        previous_value=previous_text,
        new_value=new_text,
        effective_from=effective_from,
        reason=reason,
        changed_by=changed_by,
    )
    db.add(row)
    return row


def apply_change(
    db: Session,
    employee: Employee,
    field: str,
    new: object,
    *,
    effective_from: date,
    reason: str | None,
    changed_by: str | None,
) -> bool:
    """Record and apply one field change. Returns whether anything changed."""
    previous = getattr(employee, field)
    row = record_change(
        db,
        employee,
        field,
        previous,
        new,
        effective_from=effective_from,
        reason=reason,
        changed_by=changed_by,
    )
    if row is None:
        return False
    setattr(employee, field, new)
    return True


def ensure_manager_available(
    db: Session, employee: Employee, manager_id: int | None
) -> None:
    """Refuse a self-manager or a reporting cycle."""
    if manager_id is None or manager_id == employee.id:
        if manager_id == employee.id:
            raise validation(
                "validation_error", "An employee cannot be their own manager."
            )
        return
    seen = {employee.id}
    cursor = manager_id
    while cursor is not None:
        if cursor in seen:
            raise validation(
                "validation_error",
                "That manager would close a reporting cycle.",
                employee_id=employee.id,
                manager_id=manager_id,
            )
        seen.add(cursor)
        parent = db.get(Employee, cursor)
        if parent is None:
            raise validation(
                "validation_error",
                "The manager does not exist.",
                manager_id=manager_id,
            )
        cursor = parent.manager_id


def next_termination_date(
    employee: Employee, effective_from: date
) -> date | None:
    """The termination date a move to `Terminated` should carry."""
    return employee.termination_date or effective_from


def today_minus(days: int) -> date:
    """Small helper kept for tests and callers that date a correction."""
    return date.today() - timedelta(days=days)
