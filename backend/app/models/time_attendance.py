from sqlalchemy import (
    String,
    Integer,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    Text,
    Identity,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base
import enum


class ViolationKind(str, enum.Enum):
    """Types of working time violations detected against the roster."""
    EARLY_ARRIVAL = "early_arrival"
    LATE_ARRIVAL = "late_arrival"
    EARLY_DEPARTURE = "early_departure"
    LATE_DEPARTURE = "late_departure"
    MISSING_ENTRY = "missing_entry"
    EXTRA_ENTRY = "extra_entry"


class ViolationSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CorrectionStatus(str, enum.Enum):
    """Lifecycle of an employee's request to fix a clock record."""
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class TimeEntry(Base):
    """A single clock-in/clock-out record for an employee on a work day."""

    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    work_date: Mapped[Date] = mapped_column(Date, nullable=False)
    clock_in: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clock_out: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    break_minutes: Mapped[int] = mapped_column(Integer, default=0)
    worked_hours: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    overtime_hours: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    source: Mapped[str] = mapped_column(String(20), default="Web")  # Web, Mobile, Biometric, Manual
    status: Mapped[str] = mapped_column(String(20), default="Draft")  # Draft, Approved
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    roster_entry_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("roster_entries.id"), nullable=True, index=True
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("Employee")
    roster_entry = relationship("RosterEntry", back_populates="time_entries")


class WorkingTimeViolation(Base):
    """A detected breach of the roster schedule (working time rules)."""

    __tablename__ = "working_time_violations"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    work_date: Mapped[Date] = mapped_column(Date, nullable=False)
    roster_entry_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("roster_entries.id"), nullable=True
    )
    time_entry_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("time_entries.id"), nullable=True
    )
    kind: Mapped[ViolationKind] = mapped_column(
        SQLEnum(ViolationKind), nullable=False
    )
    severity: Mapped[ViolationSeverity] = mapped_column(
        SQLEnum(ViolationSeverity), nullable=False
    )
    minutes: Mapped[int] = mapped_column(Integer, default=0)  # Minutes of deviation
    detected_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved: Mapped[bool] = mapped_column(default=False)

    employee = relationship("Employee")
    roster_entry = relationship("RosterEntry")
    time_entry = relationship("TimeEntry")


class Timesheet(Base):
    """A payroll-period summary rolled up from time entries."""

    __tablename__ = "timesheets"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    period_start: Mapped[Date] = mapped_column(Date, nullable=False)
    period_end: Mapped[Date] = mapped_column(Date, nullable=False)
    total_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    overtime_hours: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    entry_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="Draft")  # Draft, Submitted, Approved
    generated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("Employee")


class TimeCorrectionRequest(Base):
    """An employee's request to fix a clock record for a work day.

    The correction never edits the entry directly: a manager approves or
    rejects it, and the approval applies the requested times to the entry.
    """

    __tablename__ = "time_correction_requests"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    time_entry_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("time_entries.id"), nullable=True
    )
    work_date: Mapped[Date] = mapped_column(Date, nullable=False)
    requested_clock_in: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    requested_clock_out: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    requested_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    decided_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("Employee")


class AttendancePeriodLock(Base):
    """A locked attendance period: no writes for work days inside it.

    A lock row with ``is_locked`` true closes the period; reopening flips
    the flag rather than deleting the row, so the history of the lock is
    kept.
    """

    __tablename__ = "attendance_period_locks"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    period_start: Mapped[Date] = mapped_column(Date, nullable=False)
    period_end: Mapped[Date] = mapped_column(Date, nullable=False)
    is_locked: Mapped[bool] = mapped_column(default=True)
    locked_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    locked_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reopened_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    reopened_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
