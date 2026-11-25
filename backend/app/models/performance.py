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


class Goal(Base):
    """A performance goal / OKR for an employee."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[float] = mapped_column(Numeric(5, 2), default=0)  # percent weight
    progress: Mapped[float] = mapped_column(Numeric(5, 2), default=0)  # 0-100
    status: Mapped[str] = mapped_column(String(20), default="Not Started")  # Not Started, In Progress, Completed, Cancelled
    due_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("Employee")


class PerformanceReview(Base):
    """A periodic performance review."""

    __tablename__ = "performance_reviews"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    reviewer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    period: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. "2026-H1"
    status: Mapped[str] = mapped_column(String(20), default="Draft")  # Draft, In Progress, Submitted, Finalized
    overall_rating: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)  # 1-5
    manager_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    employee_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    finalized_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employee = relationship("Employee")
    feedback = relationship("ReviewFeedback", back_populates="review")


class ReviewFeedback(Base):
    """360-degree feedback entry on a review."""

    __tablename__ = "review_feedback"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    review_id: Mapped[int] = mapped_column(Integer, ForeignKey("performance_reviews.id"), nullable=False)
    from_employee_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(20), default="Peer")  # Self, Manager, Peer, Upward
    rating: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    review = relationship("PerformanceReview", back_populates="feedback")


class CompensationBand(Base):
    """Salary band for a job/level."""

    __tablename__ = "compensation_bands"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=False)
    level: Mapped[str] = mapped_column(String(40), nullable=False)  # Junior, Mid, Senior, Lead, Principal
    min_salary: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    mid_salary: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    max_salary: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job")


class MeritCycle(Base):
    """An annual merit/increment cycle."""

    __tablename__ = "merit_cycles"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)  # % of payroll budget
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Draft")  # Draft, Active, Closed
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MeritAllocation(Base):
    """Per-employee merit increase allocation."""

    __tablename__ = "merit_allocations"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    cycle_id: Mapped[int] = mapped_column(Integer, ForeignKey("merit_cycles.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    current_salary: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    proposed_salary: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    increase_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="Draft")  # Draft, Approved, Applied
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cycle = relationship("MeritCycle")
    employee = relationship("Employee")
