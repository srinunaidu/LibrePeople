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


class ComplianceRule(Base):
    """A compliance rule (labor law, policy, certification)."""

    __tablename__ = "compliance_rules"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="Labor Law")  # Labor Law, Policy, Certification, Safety
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="Medium")  # Low, Medium, High, Critical
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComplianceViolation(Base):
    """A detected compliance violation."""

    __tablename__ = "compliance_violations"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey("compliance_rules.id"), nullable=False)
    detected_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default="Open")  # Open, In Progress, Resolved, Dismissed
    resolved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee = relationship("Employee")
    rule = relationship("ComplianceRule")


class HeadcountPlan(Base):
    """A headcount plan for a period / department."""

    __tablename__ = "headcount_plans"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    department_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.id"), nullable=True)
    planned_headcount: Mapped[int] = mapped_column(Integer, default=0)
    actual_headcount: Mapped[int] = mapped_column(Integer, default=0)
    budget: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    department = relationship("Department")


class Scenario(Base):
    """A workforce planning scenario (what-if)."""

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("headcount_plans.id"), nullable=True)
    adjustments_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReportDefinition(Base):
    """A saved report definition."""

    __tablename__ = "report_definitions"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)  # SQL or report key
    filters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SavedReport(Base):
    """A saved instance of a report (snapshot)."""

    __tablename__ = "saved_reports"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    definition_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("report_definitions.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
