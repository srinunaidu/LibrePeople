"""Writing an imported leave balance through the leave ledger.

Why the import writes the ledger
--------------------------------
A leave balance used to be three numbers on a row, and the CSV import wrote
those three numbers straight into the table. The leave ledger — workforce
core's ``app/services/leave.py`` — changed that: the balance is now the sum
of a signed ledger, the three columns on ``leave_balances`` are a cache of
that sum, and a balance that moves without a row to account for it is
refused.

The import did not go through that rule. A balance that arrived from a file
had no history at all, and the reconciliation reported it as ``no_ledger``
rather than as a discrepancy. A balance that cannot be reconciled is not a
balance the product can account for, and the import is how a customer's
leave balances arrive in the first place.

So the import writes the ledger. A leave-balance row in the file becomes
ledger rows with the ledger's own semantics:

* an ``entitlement`` row for the days entitled,
* a ``carry_over`` row for the days brought forward,
* a ``usage`` row for the days taken,

and the three cached columns are refreshed from those rows **by the ledger
itself**. The import never writes the cached columns: they are the ledger's
projection, and the ledger owns them.

What the import refuses
-----------------------
The import refuses what the ledger would refuse, with the row's own error.

* **A row of zero days records nothing.** A balance that would be left with
  no ledger row behind it is not imported: it is exactly the balance the
  reconciliation cannot see.
* **The ledger's vocabulary adds days to a balance; it does not take them
  off.** The ledger maps its rows onto three cached columns, and every
  entry type it offers adds days to one of them. A file that would *lower*
  an entitlement, a carry-over or the usage is therefore refused, rather
  than being written as a balance whose history does not explain it.

That second rule is a real limitation, and it is workforce core's to lift:
the ledger already writes a reversal — a usage row with the other sign —
when a leave request is cancelled, but it exposes no public writer for one,
so the import cannot ask for it. The refusal is explicit and names the
column it refused; it is not a silent loss of the row.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.imports.errors import ErrorCode, RowError
from app.models.leave import LeaveBalance, LeaveLedgerEntryType
from app.services import leave as leave_service

#: The entity that is written through the ledger.
LEDGER_ENTITY = "leave_balances"

#: The three cached columns, in the order the ledger's buckets use them.
DAY_COLUMNS = ("entitled_days", "carried_over_days", "used_days")

#: The ledger entry type that carries each cached column.
ENTRY_TYPES = (
    LeaveLedgerEntryType.ENTITLEMENT,
    LeaveLedgerEntryType.CARRY_OVER,
    LeaveLedgerEntryType.USAGE,
)

#: The reference type the rows an import writes carry.
REFERENCE_TYPE = "import"

#: What each kind of movement is called. The description says what the
#: movement was. It never says anything about the person.
DESCRIPTIONS = {
    LeaveLedgerEntryType.ENTITLEMENT: (
        "Entitlement imported from the customer's leave balance file"
    ),
    LeaveLedgerEntryType.CARRY_OVER: (
        "Carry-over imported from the customer's leave balance file"
    ),
    LeaveLedgerEntryType.USAGE: (
        "Usage imported from the customer's leave balance file"
    ),
}

ZERO = Decimal("0")


def _decimal(value: Any) -> Decimal:
    """A decimal from whatever the analysis produced."""
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass
class LedgerPlan:
    """What one imported leave-balance row will write.

    ``status``
        ``create``, ``update`` or ``unchanged`` — the same words the rest
        of the importer uses, so the dry run and the commit agree.
    ``entries``
        The ledger rows to write, as ``(entry type, days)`` pairs. The days
        are the size of the movement; the sign is the entry type's own.
    ``error``
        The refusal, when the ledger would refuse the row.
    """

    status: str
    entries: list[tuple[LeaveLedgerEntryType, Decimal]] = field(
        default_factory=list
    )
    error: RowError | None = None

    @property
    def refused(self) -> bool:
        return self.error is not None


def projection(
    db: Session, balance: LeaveBalance
) -> tuple[Decimal, Decimal, Decimal]:
    """The balance's three cached numbers, read out of its ledger rows.

    This is the ledger's own projection — the same function the leave
    service refreshes the cache with — so the import compares a file
    against the history, not against a cached number that may be stale.
    """
    return leave_service.buckets(leave_service.ledger_rows(db, balance))


def has_history(db: Session, balance: LeaveBalance) -> bool:
    """Whether the balance has any ledger row behind it."""
    return bool(leave_service.ledger_rows(db, balance))


def plan_row(
    db: Session,
    balance: LeaveBalance | None,
    values: dict[str, Any],
    row_number: int,
) -> LedgerPlan:
    """What the row would write, given the balance's ledger.

    ``balance`` is ``None`` when the balance does not exist yet. ``values``
    holds the columns the file actually supplied; a column the file did
    not supply keeps the value it has, which is the rule the rest of the
    importer follows.

    The plan is the *difference* between the balance's history and what
    the file states, expressed as the ledger's own movements. A file that
    states what the ledger already says writes nothing.
    """
    current = (
        projection(db, balance) if balance is not None else (ZERO, ZERO, ZERO)
    )
    target = list(current)
    for index, column in enumerate(DAY_COLUMNS):
        supplied = values.get(column)
        if supplied is not None:
            target[index] = _decimal(supplied)

    entries: list[tuple[LeaveLedgerEntryType, Decimal]] = []
    for index, (column, entry_type) in enumerate(zip(DAY_COLUMNS, ENTRY_TYPES)):
        movement = target[index] - current[index]
        if movement == 0:
            continue
        if movement < 0:
            return LedgerPlan(
                status="reject",
                error=RowError(
                    row_number,
                    column,
                    ErrorCode.LEDGER_REDUCTION_REFUSED,
                    f"'{column}' cannot be lowered by an import: the leave "
                    "ledger only records days coming to a balance. Adjust "
                    "the balance through the leave ledger instead.",
                ),
            )
        entries.append((entry_type, movement))

    if not entries:
        # Nothing to write. That is only right when the balance already
        # has the history that explains it. A balance with no ledger row
        # behind it is a balance the reconciliation cannot see, so the row
        # is refused rather than written.
        if balance is None or not has_history(db, balance):
            return LedgerPlan(
                status="reject",
                error=RowError(
                    row_number,
                    DAY_COLUMNS[0],
                    ErrorCode.LEDGER_NO_MOVEMENT,
                    "A leave balance of zero days leaves no ledger row "
                    "behind it, so it is not imported.",
                ),
            )
        return LedgerPlan(status="unchanged", entries=[])

    return LedgerPlan(
        status="create" if balance is None else "update",
        entries=entries,
    )


def new_balance(spec, key: tuple) -> LeaveBalance:
    """The balance a row creates, from the row's natural key.

    The key is the *resolved* one — the employee's id, the leave type's
    id and the year — so the balance is written against the records the
    row named and not against the names.
    """
    employee_id, leave_type_id, entitlement_year = key
    return spec.model(
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        entitlement_year=entitlement_year,
    )


def write_entries(
    db: Session,
    balance: LeaveBalance,
    entries: list[tuple[LeaveLedgerEntryType, Decimal]],
    *,
    reference_id: int | None = None,
    created_by: int | None = None,
) -> list[Any]:
    """Write the ledger rows, and let the ledger refresh the cache.

    Every row is written through the leave service's own writer, so the
    sign rules, the cache refresh and the guard that refuses a balance
    that moves without a row are the ledger's, not the importer's. The
    importer does not commit: the rows and the balance they explain are
    written in the caller's transaction.
    """
    written = []
    for entry_type, days in entries:
        # A usage takes days from the balance, so its movement is the
        # other way round. The sign is the entry type's own rule.
        signed = -days if entry_type is LeaveLedgerEntryType.USAGE else days
        written.append(
            leave_service.post_entry(
                db,
                balance,
                entry_type,
                signed,
                reference_type=REFERENCE_TYPE,
                reference_id=reference_id,
                description=DESCRIPTIONS[entry_type],
                created_by=created_by,
            )
        )
    return written
