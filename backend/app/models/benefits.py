from sqlalchemy import (
    String,
    Boolean,
    Integer,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    Text,
    Identity,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base


class BenefitPlan(Base):
    """A benefit plan offered to employees."""

    __tablename__ = "benefit_plans"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    plan_type: Mapped[str] = mapped_column(String(30), nullable=False)  # Health, Dental, Vision, Life, Retirement, Other
    provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    employer_contribution: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    employee_contribution: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BenefitEnrollment(Base):
    """An employee's enrollment in a benefit plan."""

    __tablename__ = "benefit_enrollments"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("benefit_plans.id"), nullable=False)
    effective_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Active")  # Active, Terminated, Waived
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee")
    plan = relationship("BenefitPlan")


class LifeEvent(Base):
    """A life event that may trigger benefit changes."""

    __tablename__ = "life_events"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)  # Marriage, Birth, Adoption, Divorce, Death, JobChange
    event_date: Mapped[Date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending, Processed
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee")


class LeaveOfAbsence(Base):
    """A leave of absence (FMLA, parental, medical, etc.)."""

    __tablename__ = "leaves_of_absence"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type: Mapped[str] = mapped_column(String(40), nullable=False)  # FMLA, Parental, Medical, Bereavement, Sabbatical
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending, Approved, Denied, Completed
    approved_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee")
