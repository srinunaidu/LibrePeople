"""Saved views and scheduled reporting for read-only reports (LP-REP personalization).

Part E — saved views: REPORTS_ROLES users persist named filter sets for the
existing read-only reports (joiners/leavers/attrition/payroll-summary) and
reopen shared views published to their role.

Part F — scheduled reporting: REPORTS_ROLES users create schedules (report
key + stored filters + frequency + timezone) with explicit recipients. A due
tick enqueues a ``REPORT_RUN`` job on the existing queue; the existing
``JobWorker`` executes it. Delivery is an in-app ``Notification`` row per
recipient with a download link rendered through the existing
``report_exports`` path. Execution is runs-as-owner: data is resolved with
the owner's visibility and the owner's role mask, and a recipient outside
the report's role set gets a notice instead of data.

No change to existing report calculations, masking, or CSV/XLSX bytes.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ReportSavedView(Base):
    """A named filter set for a read-only report, owned by one user."""

    __tablename__ = "report_saved_views"
    __table_args__ = (
        Index("ix_report_saved_views_tenant_owner", "tenant_id", "owner_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    report_key: Mapped[str] = mapped_column(String(40), nullable=False)
    filters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: ``personal`` (owner only) or ``shared`` (roles that can view the
    #: report; publishing requires HR/SuperAdmin).
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="personal")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class ReportSchedule(Base):
    """A recurring report delivery owned by one user."""

    __tablename__ = "report_schedules"
    __table_args__ = (
        Index("ix_report_schedules_tenant_owner", "tenant_id", "owner_id"),
        Index("ix_report_schedules_due", "active", "next_due_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    report_key: Mapped[str] = mapped_column(String(40), nullable=False)
    filters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: ``daily`` | ``weekly`` | ``monthly``.
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")
    #: IANA timezone name; defaults to the tenant timezone (D1).
    timezone: Mapped[str] = mapped_column(String(80), nullable=False, default="UTC")
    #: JSON list of recipient user ids.
    recipient_ids_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Output format: ``csv`` or ``xlsx`` (existing export path).
    output_format: Mapped[str] = mapped_column(String(10), nullable=False, default="csv")
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class ReportRun(Base):
    """One executed (or attempted) delivery of a schedule."""

    __tablename__ = "report_runs"
    __table_args__ = (
        Index("ix_report_runs_schedule", "schedule_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(Integer, nullable=False)
    job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: ``delivered`` | ``partial`` | ``failed`` | ``dead``.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="failed")
    #: Recipient count the run attempted (for the audit row).
    recipient_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: Rendered payload: CSV text, or base64 for xlsx.
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_format: Mapped[str | None] = mapped_column(String(10), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
