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


class Course(Base):
    """A training course in the learning catalog."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(60), default="General")  # Compliance, Technical, Leadership, Soft Skills
    duration_hours: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CourseEnrollment(Base):
    """An employee's enrollment in a course."""

    __tablename__ = "course_enrollments"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey("courses.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Enrolled")  # Enrolled, In Progress, Completed, Failed
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee")
    course = relationship("Course")


class Certification(Base):
    """A certification held by an employee."""

    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    issued_date: Mapped[Date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    certificate_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee")


class TalentPool(Base):
    """A pool of high-potential / successor candidates."""

    __tablename__ = "talent_pools"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TalentPoolMember(Base):
    """An employee in a talent pool."""

    __tablename__ = "talent_pool_members"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    pool_id: Mapped[int] = mapped_column(Integer, ForeignKey("talent_pools.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    readiness: Mapped[str] = mapped_column(String(20), default="Ready in 2-3 years")  # Ready Now, Ready in 1-2 years, Ready in 2-3 years
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pool = relationship("TalentPool")
    employee = relationship("Employee")


class SuccessionPlan(Base):
    """Succession plan for a key position."""

    __tablename__ = "succession_plans"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    position_id: Mapped[int] = mapped_column(Integer, ForeignKey("positions.id"), nullable=False)
    primary_successor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    backup_successor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    readiness: Mapped[str] = mapped_column(String(40), default="Ready in 2-3 years")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    position = relationship("Position")
    primary_successor = relationship("Employee", foreign_keys=[primary_successor_id])
    backup_successor = relationship("Employee", foreign_keys=[backup_successor_id])
