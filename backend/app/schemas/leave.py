"""The leave domain's request and response shapes.

The balance is derived from the ledger, so the shape that answers "how much
leave is left" carries the derived figure and the cached one beside it. A
client that wants to know whether the two agree can see it; a client that
only wants the balance reads one number.
"""
from datetime import date, datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class LeaveTypeCreate(BaseModel):
    name: str
    code: str
    is_paid: bool = True
    # The number of days a year of this type grants. ``default_days`` is the
    # older spelling of the same number and is still accepted: a client that
    # sends it used to have it dropped silently, which granted an entitlement
    # of nothing.
    max_days_per_year: float = Field(
        default=0,
        validation_alias=AliasChoices("max_days_per_year", "default_days"),
    )
    is_active: bool = True

    model_config = ConfigDict(populate_by_name=True)


class LeaveTypeUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    is_paid: Optional[bool] = None
    max_days_per_year: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("max_days_per_year", "default_days"),
    )
    is_active: Optional[bool] = None

    model_config = ConfigDict(populate_by_name=True)


class LeaveTypeOut(LeaveTypeCreate):
    id: int

    class Config:
        from_attributes = True


class EntitlementCreate(BaseModel):
    entitlement_year: int
    leave_type_id: Optional[int] = None
    entitled_days: Optional[float] = None
    carried_over_days: float = 0


class AccrualRunRequest(BaseModel):
    """Enqueue one month's leave accrual as a background job.

    The job posts ``round(max_days_per_year / 12, 2)`` per active employee
    and leave type, plus the January carry-over of the prior year's unused
    balance in full (no cap field exists on the leave type). Re-running for
    the same month is a no-op: the queue returns the succeeded job.
    """

    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    leave_type_id: Optional[int] = None


class AccrualRunOut(BaseModel):
    job_id: int
    job_type: str
    state: str


class LeaveBalanceOut(BaseModel):
    """A leave balance, and the cache it is derived from.

    ``available_days`` is the **derived** balance: the sum of the signed
    ledger rows. ``cached_available_days`` is what the balance row's own
    columns add up to, which is the same number when the two are in step and
    a discrepancy when they are not.
    """

    id: int
    employee_id: int
    leave_type_id: int
    entitlement_year: int
    entitled_days: float
    carried_over_days: float
    used_days: float
    available_days: float
    cached_available_days: float
    leave_type_name: Optional[str] = None

    class Config:
        from_attributes = True


class LeaveLedgerEntryOut(BaseModel):
    """One movement of a leave balance.

    A row is never edited and never deleted. A correcting movement is
    appended, and it references the row it corrects.
    """

    id: int
    balance_id: int
    employee_id: int
    leave_type_id: int
    entitlement_year: int
    entry_type: str
    signed_days: float
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    running_balance: float
    source: str

    class Config:
        from_attributes = True


class LeaveReconciliationRow(BaseModel):
    """One balance, read against the ledger that should explain it."""

    balance_id: int
    employee_id: int
    leave_type_id: int
    leave_type_name: Optional[str] = None
    entitlement_year: int
    cached_entitled_days: float
    cached_carried_over_days: float
    cached_used_days: float
    cached_available_days: float
    ledger_available_days: float
    difference_days: float
    ledger_entries: int
    state: str

    class Config:
        from_attributes = True


class LeaveReconciliationSummary(BaseModel):
    """What the reconciliation found, in one line of numbers."""

    balances: int = 0
    in_sync: int = 0
    out_of_sync: int = 0
    no_ledger: int = 0
    difference_days: float = 0


class LeaveReconciliationOut(BaseModel):
    """The reconciliation of a tenant's balances against their ledgers."""

    year: Optional[int] = None
    rows: list[LeaveReconciliationRow] = []
    summary: LeaveReconciliationSummary = LeaveReconciliationSummary()


class LeavePayrollInputEntry(BaseModel):
    """One piece of approved leave, quantified, for the payroll lane."""

    employee_id: int
    leave_type_id: int
    leave_type_code: str
    is_paid: bool
    leave_request_id: int
    start_date: date
    end_date: date
    quantity_days: float

    class Config:
        from_attributes = True


class LeavePayrollInputOut(BaseModel):
    """The approved leave of a period, in the shape the payroll lane reads."""

    period_start: date
    period_end: date
    entries: list[LeavePayrollInputEntry] = []
    total_days: float = 0


class LeaveRequestCreate(BaseModel):
    employee_id: int
    leave_type_id: int
    start_date: date
    end_date: date
    reason: Optional[str] = None


class LeaveRequestUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None


class LeaveRequestOut(BaseModel):
    id: int
    employee_id: int
    leave_type_id: int
    start_date: date
    end_date: date
    working_days: float
    reason: Optional[str] = None
    status: str
    decided_by: Optional[int] = None
    decided_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    balance_applied: bool = False

    class Config:
        from_attributes = True
