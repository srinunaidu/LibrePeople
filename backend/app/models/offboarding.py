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


class Termination(Base):
    """An offboarding / separation case for an employee."""

    __tablename__ = "terminations"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    last_working_date: Mapped[Date] = mapped_column(Date, nullable=False)
    termination_type: Mapped[str] = mapped_column(String(30), default="Resignation")  # Resignation, Termination, Layoff, Retirement, End of Contract
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Initiated")  # Initiated, In Progress, Completed, Cancelled
    exit_interview_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_pay_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    initiated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    initiated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("Employee")
    items = relationship("OffboardingItem", back_populates="termination")


class OffboardingTask(Base):
    """A reusable offboarding checklist task (template)."""

    __tablename__ = "offboarding_tasks"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(40), default="General")  # IT, HR, Finance, Facilities, General
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    default_assignee_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OffboardingItem(Base):
    """A checklist item instantiated for a specific termination."""

    __tablename__ = "offboarding_items"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    termination_id: Mapped[int] = mapped_column(Integer, ForeignKey("terminations.id"), nullable=False)
    task_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("offboarding_tasks.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="General")
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    due_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending, Completed
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    termination = relationship("Termination", back_populates="items")
