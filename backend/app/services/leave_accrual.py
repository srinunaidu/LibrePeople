"""Monthly leave accrual and January carry-over, run as a background job.

Formula (documented here because no policy engine is invented)
-------------------------------------------------------------
* **Monthly accrual**, for one (employee, leave type) pair::

      accrual = round(max_days_per_year / 12, 2)

  ``LeaveType`` carries no monthly-rate and no carry-over-cap field, so no
  cap is applied: the only grant parameter the product has is
  ``max_days_per_year``. A type with ``max_days_per_year == 0`` accrues
  nothing and is skipped.
* **Carry-over** (January runs only): the prior year's *derived* balance —
  the sum of its ledger rows, floored at zero — is posted in full as a
  ``CARRY_OVER`` row on the new year's balance. Because no cap field
  exists on ``LeaveType``, the whole unused balance carries; introducing a
  cap would be a new product decision, not this job.
* **No year-end true-up**: twelve rounded monthly postings can differ from
  ``max_days_per_year`` by a few cents. That drift is accepted and stays
  visible in the ledger rather than being silently corrected.

Idempotency
-----------
* Queue level: the job is enqueued with the input ``{year, month, ...}``
  and the queue deduplicates on ``(job_type, input_hash)`` for jobs that
  already succeeded.
* Row level: an ``ACCRUAL`` row with ``reference_type="accrual"`` and
  ``reference_id=YYYYMM`` is posted at most once per balance; a
  ``CARRY_OVER`` row with ``reference_type="carry_over"`` and
  ``reference_id=YYYY`` (the target year) at most once. A re-run skips
  what exists and reports the skips.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.booleans import is_true
from app.models.employee import Employee
from app.models.leave import (
    LeaveBalance,
    LeaveLedger,
    LeaveLedgerEntryType,
    LeaveType,
)
from app.services import leave as ledger

#: Ledger references written by this job. ``reference_type`` values are
#: shared with the entitlement path, but the ``reference_id`` values below
#: are only ever written here, so the idempotency checks cannot collide
#: with a manual grant (whose ``reference_id`` is NULL).
ACCRUAL_REFERENCE_TYPE = "accrual"
CARRY_OVER_REFERENCE_TYPE = "carry_over"

_CENTS = Decimal("0.01")


def accrual_reference_id(year: int, month: int) -> int:
    """The ledger ``reference_id`` for one month's accrual: ``YYYYMM``."""
    return year * 100 + month


def monthly_amount(leave_type: LeaveType) -> Decimal:
    """One month's accrual for a leave type (see the module formula)."""
    base = Decimal(str(leave_type.max_days_per_year or 0))
    return (base / Decimal(12)).quantize(_CENTS, rounding=ROUND_HALF_UP)


def run_accrual(
    db: Session,
    year: int,
    month: int,
    *,
    leave_type_id: Optional[int] = None,
    created_by: Optional[int] = None,
) -> dict[str, Any]:
    """Post one month's accrual (and January carry-over) for every balance.

    Balances that do not exist yet are created empty beside their first
    accrual row, the same way entitlements always write the balance and its
    rows together. The caller commits: this stages rows only.
    """
    if not isinstance(year, int) or not isinstance(month, int):
        raise ValueError("accrual needs an integer 'year' and 'month'")
    if month < 1 or month > 12:
        raise ValueError(f"month must be 1-12, got {month}")

    employees = (
        db.query(Employee).filter(Employee.status == "Active").all()
    )
    if leave_type_id is not None:
        leave_type = (
            db.query(LeaveType).filter(LeaveType.id == leave_type_id).first()
        )
        if leave_type is None:
            raise ValueError(f"leave type {leave_type_id} does not exist")
        types = [leave_type]
    else:
        types = (
            db.query(LeaveType).filter(is_true(LeaveType.is_active)).all()
        )

    ref_id = accrual_reference_id(year, month)
    stats = {
        "year": year,
        "month": month,
        "accruals_posted": 0,
        "accruals_skipped_duplicate": 0,
        "accruals_skipped_zero_grant": 0,
        "carry_overs_posted": 0,
        "carry_overs_skipped_duplicate": 0,
        "carry_overs_skipped_empty": 0,
    }
    for employee in employees:
        for leave_type in types:
            amount = monthly_amount(leave_type)
            if amount <= 0:
                stats["accruals_skipped_zero_grant"] += 1
                continue
            balance = ledger.find_balance(
                db, employee.id, leave_type.id, year
            )
            if balance is None:
                balance = LeaveBalance(
                    employee_id=employee.id,
                    leave_type_id=leave_type.id,
                    entitlement_year=year,
                    entitled_days=Decimal("0"),
                    carried_over_days=Decimal("0"),
                    used_days=Decimal("0"),
                )
                db.add(balance)
                db.flush()
            duplicate = (
                db.query(LeaveLedger)
                .filter(
                    LeaveLedger.balance_id == balance.id,
                    LeaveLedger.entry_type == LeaveLedgerEntryType.ACCRUAL,
                    LeaveLedger.reference_type == ACCRUAL_REFERENCE_TYPE,
                    LeaveLedger.reference_id == ref_id,
                )
                .first()
            )
            if duplicate is not None:
                stats["accruals_skipped_duplicate"] += 1
            else:
                ledger.post_entry(
                    db,
                    balance,
                    LeaveLedgerEntryType.ACCRUAL,
                    amount,
                    reference_type=ACCRUAL_REFERENCE_TYPE,
                    reference_id=ref_id,
                    description=f"Monthly accrual for {year}-{month:02d}",
                    created_by=created_by,
                )
                stats["accruals_posted"] += 1
            if month == 1:
                _carry_over(db, balance, year, created_by, stats)
    return stats


def _carry_over(
    db: Session,
    balance: LeaveBalance,
    year: int,
    created_by: Optional[int],
    stats: dict[str, Any],
) -> None:
    """Post the prior year's unused balance onto ``balance`` (January only)."""
    duplicate = (
        db.query(LeaveLedger)
        .filter(
            LeaveLedger.balance_id == balance.id,
            LeaveLedger.entry_type == LeaveLedgerEntryType.CARRY_OVER,
            LeaveLedger.reference_type == CARRY_OVER_REFERENCE_TYPE,
            LeaveLedger.reference_id == year,
        )
        .first()
    )
    if duplicate is not None:
        stats["carry_overs_skipped_duplicate"] += 1
        return
    prior = ledger.find_balance(
        db, balance.employee_id, balance.leave_type_id, year - 1
    )
    if prior is None:
        stats["carry_overs_skipped_empty"] += 1
        return
    unused = ledger.derived_available_days(db, prior)
    if unused <= 0:
        stats["carry_overs_skipped_empty"] += 1
        return
    ledger.post_entry(
        db,
        balance,
        LeaveLedgerEntryType.CARRY_OVER,
        unused,
        reference_type=CARRY_OVER_REFERENCE_TYPE,
        reference_id=year,
        description=f"Days carried forward from {year - 1}",
        created_by=created_by,
    )
    stats["carry_overs_posted"] += 1
