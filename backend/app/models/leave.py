from sqlalchemy import (
    String,
    Boolean,
    CheckConstraint,
    Integer,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    Text,
    Identity,
    UniqueConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base
import enum
from decimal import Decimal

#: NFR-014 safe constraints (migration 0043_integrity_expand). Shared
#: texts so the models and the migration cannot disagree; every name is
#: at most 30 characters for Oracle.
#: C7: a request's window is ordered.
LEAVE_REQ_DATES_CHECK = "start_date <= end_date"
#: C8: the request FSM the leave endpoint walks.
LEAVE_REQ_STATUS_CHECK = "status IN ('Pending','Approved','Rejected','Cancelled')"
#: C9: a zero-effect row moves no balance and only hides in the ledger.
LEDGER_SIGNED_CHECK = "signed_days <> 0"


class LeaveLedgerEntryType(str, enum.Enum):
    """Types of leave ledger entries — every balance change is one row."""
    ACCRUAL = "accrual"           # Periodic grant (e.g., monthly accrual)
    ENTITLEMENT = "entitlement"   # Annual entitlement grant (base + tenure)
    CARRY_OVER = "carry_over"     # Brought forward from prior year
    USAGE = "usage"               # Approved leave request consumption
    ADJUSTMENT = "adjustment"     # Manual correction (HR/admin)
    EXPIRY = "expiry"             # Use-it-or-lose-it expiry
    ENCASHMENT = "encashment"     # Conversion to pay


class LeaveType(Base):
    """A category of leave (Annual, Sick, Casual, ...)."""

    __tablename__ = "leave_types"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True)
    max_days_per_year: Mapped[float] = mapped_column(Numeric(6, 1), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    balances = relationship("LeaveBalance", back_populates="leave_type")
    ledger_entries = relationship("LeaveLedger", back_populates="leave_type")


class LeaveBalance(Base):
    """Annual entitlement and usage for one employee / leave type / year.

    Balance is DERIVED from the ledger: sum of signed ledger entries.
    The stored fields (entitled_days, carried_over_days, used_days) are
    cached aggregates for query performance; they MUST equal the ledger sum.
    """

    __tablename__ = "leave_balances"
    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type_id", "entitlement_year", name="uq_leave_balance"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("leave_types.id"), nullable=False)
    entitlement_year: Mapped[int] = mapped_column(Integer, nullable=False)
    entitled_days: Mapped[Decimal] = mapped_column(Numeric(6, 1), default=Decimal("0"))
    carried_over_days: Mapped[Decimal] = mapped_column(Numeric(6, 1), default=Decimal("0"))
    used_days: Mapped[Decimal] = mapped_column(Numeric(6, 1), default=Decimal("0"))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    leave_type = relationship("LeaveType", back_populates="balances")
    ledger_entries = relationship("LeaveLedger", back_populates="balance")

    @property
    def available_days(self) -> Decimal:
        return ((self.entitled_days or Decimal("0")) + (self.carried_over_days or Decimal("0")) - (self.used_days or Decimal("0"))).quantize(Decimal("0.01"))

    def compute_from_ledger(self, db) -> Decimal:
        """Recalculate balance from ledger entries (for verification)."""
        from sqlalchemy import func as sqlfunc
        result = db.query(sqlfunc.coalesce(sqlfunc.sum(LeaveLedger.signed_days), Decimal("0"))).filter(
            LeaveLedger.balance_id == self.id
        ).scalar()
        return (result or Decimal("0")).quantize(Decimal("0.01"))

    def verify_ledger_invariant(self, db) -> bool:
        """Assert balance equals sum of ledger rows."""
        ledger_sum = self.compute_from_ledger(db)
        cached = self.available_days
        return abs(ledger_sum - cached) < Decimal("0.01")


class LeaveLedger(Base):
    """Append-only ledger of every leave balance change.

    INVARIANT: For each LeaveBalance, available_days == sum(signed_days) of its ledger rows.
    """

    __tablename__ = "leave_ledger"
    __table_args__ = (
        CheckConstraint(LEDGER_SIGNED_CHECK, name="ck_ledger_signed_nonzero"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    balance_id: Mapped[int] = mapped_column(Integer, ForeignKey("leave_balances.id"), nullable=False, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    leave_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("leave_types.id"), nullable=False, index=True)
    entitlement_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    entry_type: Mapped[LeaveLedgerEntryType] = mapped_column(SQLEnum(LeaveLedgerEntryType), nullable=False)
    # Positive for accrual/entitlement/carry_over; negative for usage/adjustment/expiry/encashment
    signed_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    # Reference to the source document (request_id, adjustment_id, etc.)
    reference_type: Mapped[str | None] = mapped_column(String(40), nullable=True)  # leave_request, adjustment, entitlement_batch
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    balance = relationship("LeaveBalance", back_populates="ledger_entries")
    leave_type = relationship("LeaveType", back_populates="ledger_entries")
    employee = relationship("Employee")


class LeaveRequest(Base):
    """A leave request submitted by an employee."""

    __tablename__ = "leave_requests"
    __table_args__ = (
        CheckConstraint(LEAVE_REQ_DATES_CHECK, name="ck_leave_req_dates"),
        CheckConstraint(LEAVE_REQ_STATUS_CHECK, name="ck_leave_req_status"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("leave_types.id"), nullable=False)
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Date] = mapped_column(Date, nullable=False)
    working_days: Mapped[float] = mapped_column(Numeric(6, 1), default=0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending, Approved, Rejected, Cancelled
    decided_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Tracks whether the ledger entry was created for this request
    balance_applied: Mapped[bool] = mapped_column(Boolean, default=False)

    employee = relationship("Employee")
    leave_type = relationship("LeaveType")
