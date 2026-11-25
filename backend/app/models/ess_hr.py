from sqlalchemy import (
    String,
    Boolean,
    Integer,
    Date,
    DateTime,
    Text,
    ForeignKey,
    Identity,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base


class EmployeeSelfService(Base):
    """Employee self-service profile and preferences."""

    __tablename__ = "employee_self_service"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False, unique=True)
    preferred_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    emergency_contact_relation: Mapped[str | None] = mapped_column(String(60), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(60), nullable=True)
    bank_routing: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    direct_deposit_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_email: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_sms: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_push: Mapped[bool] = mapped_column(Boolean, default=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    theme_preference: Mapped[str] = mapped_column(String(10), default="light")  # light, dark, system
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("Employee")


class OrgChartNode(Base):
    """Cached org chart node for fast rendering."""

    __tablename__ = "org_chart_nodes"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False, unique=True)
    manager_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    path: Mapped[str | None] = mapped_column(Text, nullable=True)  # materialized path e.g. "1/5/12"
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])
    manager = relationship("Employee", foreign_keys=[manager_id])


class Notification(Base):
    """In-app and email notifications."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    recipient_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(40), nullable=False)  # info, success, warning, error, approval, reminder
    category: Mapped[str] = mapped_column(String(40), default="system")  # system, leave, payroll, recruiting, performance
    entity_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    #: Delivery of the notification through the background queue
    #: (LP-NOT-003). ``queued`` at emission; the ``notification_deliver``
    #: handler moves it to ``sending`` and then to ``sent``, or to
    #: ``failed`` (retryable) and finally ``dead`` when attempts are spent.
    #: No external vendor is involved: the in-app centre is the channel and
    #: ``email_sent`` records the intent for the email channel.
    delivery_status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipient = relationship("User")


class EmployeeFile(Base):
    """Document in an employee's file (versioned)."""

    __tablename__ = "employee_files"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(60), nullable=False)  # Contract, ID, Tax, Certificate, Policy, Review, Other
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_url: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="Active")  # Active, Archived, Expired
    expiry_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee")


class Announcement(Base):
    """Company-wide announcement."""

    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="General")  # General, HR, IT, Policy, Event
    priority: Mapped[str] = mapped_column(String(20), default="Normal")  # Low, Normal, High, Urgent
    target_audience: Mapped[str] = mapped_column(String(40), default="All")  # All, Department, Role, Location
    target_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author = relationship("User")


class EmployeeDirectory(Base):
    """Searchable employee directory entry (denormalized for fast search)."""

    __tablename__ = "employee_directory"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    department: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    job_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    employee = relationship("Employee")


class GoalAlignment(Base):
    """Links a goal to a parent goal (OKR cascading)."""

    __tablename__ = "goal_alignments"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    goal_id: Mapped[int] = mapped_column(Integer, ForeignKey("goals.id"), nullable=False)
    parent_goal_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("goals.id"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    goal = relationship("Goal", foreign_keys=[goal_id])
    parent = relationship("Goal", foreign_keys=[parent_goal_id])


class ContinuousFeedback(Base):
    """Real-time feedback between employees."""

    __tablename__ = "continuous_feedback"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    from_employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    to_employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(20), default="Praise")  # Praise, Coaching, Recognition
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    from_employee = relationship("Employee", foreign_keys=[from_employee_id])
    to_employee = relationship("Employee", foreign_keys=[to_employee_id])


class ComplianceCheck(Base):
    """Scheduled compliance check result."""

    __tablename__ = "compliance_checks"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey("compliance_rules.id"), nullable=False)
    run_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    passed: Mapped[bool] = mapped_column(Boolean, default=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    rule = relationship("ComplianceRule")
