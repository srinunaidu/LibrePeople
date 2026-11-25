from sqlalchemy import (
    String,
    Boolean,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    Text,
    Identity,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base


class ShiftTemplate(Base):
    """A reusable shift pattern (e.g. "Day 09:00-17:00")."""

    __tablename__ = "shift_templates"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    break_minutes: Mapped[int] = mapped_column(Integer, default=0)
    is_night: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    roster_entries = relationship("RosterEntry", back_populates="shift_template")


class RosterEntry(Base):
    """A scheduled shift for an employee on a specific date."""

    __tablename__ = "roster_entries"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    work_date: Mapped[Date] = mapped_column(Date, nullable=False)
    shift_template_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("shift_templates.id"), nullable=True
    )
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    is_night: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="Scheduled")  # Scheduled, Confirmed, Absent, Cancelled
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("Employee")
    shift_template = relationship("ShiftTemplate", back_populates="roster_entries")
    swaps = relationship("ShiftSwap", back_populates="roster_entry")
    time_entries = relationship("TimeEntry", back_populates="roster_entry")


class RosterVersion(Base):
    """An immutable published (or draft) version of a roster."""
    __tablename__ = "roster_versions"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    location_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    period_start: Mapped[Date] = mapped_column(Date, nullable=False)
    period_end: Mapped[Date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    published_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    published_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    solver_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ShiftSwap(Base):
    """A request to swap a rostered shift with another employee."""

    __tablename__ = "shift_swaps"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    roster_entry_id: Mapped[int] = mapped_column(Integer, ForeignKey("roster_entries.id"), nullable=False)
    requester_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    target_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    proposed_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending, Approved, Rejected
    decided_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    roster_entry = relationship("RosterEntry", back_populates="swaps")
