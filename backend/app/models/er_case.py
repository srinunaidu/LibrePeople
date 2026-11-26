"""Employee Relations (ER) confidential cases.

Gap #9: grievance, discipline, investigation and whistleblowing need a case
type of their own with strict confidentiality. This is deliberately NOT
``hr_cases``: the helpdesk grants the requester (subject) visibility of
their own case (``_ensure_can_access_case`` in ``core_hr.py``), while an ER
subject must never see — or infer — a case about themselves. Separate
tables give deny-by-default visibility.

Confidentiality rules (enforced in ``endpoints/er_cases.py``)
------------------------------------------------------------
* HR and SuperAdmin (``ADMIN_ROLES``) work the whole queue.
* Anyone else sees only the cases assigned to them (``assigned_to``) —
  never the queue, never a colleague's case, and never a case whose
  subject they are. Anything else is refused with 404, never 403.
* The reporter is always an authenticated account (``reported_by``); there
  is no anonymous intake in v1 (lead decision D1).
* There is no PIP case type and no link to the performance module in v1
  (lead decision D2).
* Closed cases keep their full history; nothing is auto-sealed (D3).

Postgres cleanliness: no database enum anywhere — ``case_type``,
``severity`` and ``status`` are plain ``String`` columns with CHECK
constraints, and the lifecycle lives in the endpoint. The CHECK texts are
duplicated in migration ``0051_er_cases`` deliberately and must stay in
sync.
"""

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Identity,
    Index,
)
from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base

#: Case types admitted in v1. No ``pip`` (lead decision D2) and no anonymous
#: intake lane (lead decision D1): every case names an authenticated reporter.
ER_CASE_TYPES = ("grievance", "discipline", "investigation", "whistleblowing")

#: Severity ladder.
ER_SEVERITIES = ("Low", "Medium", "High", "Critical")

#: The forward-only status machine. One step at a time:
#: Open > Triaged > Investigating > ActionTaken > Resolved > Closed.
#: Resolving requires a non-blank outcome; closing keeps the history (D3).
ER_STATUSES = (
    "Open",
    "Triaged",
    "Investigating",
    "ActionTaken",
    "Resolved",
    "Closed",
)

ER_CASE_TYPE_CHECK = (
    "case_type IN ('grievance','discipline','investigation','whistleblowing')"
)
ER_SEVERITY_CHECK = "severity IN ('Low','Medium','High','Critical')"
ER_STATUS_CHECK = (
    "status IN ('Open','Triaged','Investigating','ActionTaken','Resolved','Closed')"
)


class ERCase(Base):
    """A confidential employee-relations case."""

    __tablename__ = "er_cases"
    __table_args__ = (
        Index("ix_er_cases_tenant_id_id", "tenant_id", "id"),
        CheckConstraint(ER_CASE_TYPE_CHECK, name="ck_er_case_type"),
        CheckConstraint(ER_SEVERITY_CHECK, name="ck_er_severity"),
        CheckConstraint(ER_STATUS_CHECK, name="ck_er_status_fsm"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    case_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_employee_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("employees.id"), nullable=True
    )
    #: The authenticated reporter (D1). Set server-side from the identity —
    #: never taken from the payload, so a case always names who raised it.
    reported_by: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="Medium")
    status: Mapped[str] = mapped_column(String(20), default="Open")
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    classification: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    subject = relationship("Employee")


class ERCaseComment(Base):
    """An append-only comment on an ER case.

    The API offers no update or delete for comments, so the rows behind a
    case are its ordered investigation history — kept even after close (D3).
    """

    __tablename__ = "er_case_comments"
    __table_args__ = (
        Index("ix_er_case_comments_case_id", "case_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("er_cases.id"), nullable=False
    )
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    case = relationship("ERCase")


class ERCaseAttachment(Base):
    """One file attached to an ER case.

    The file itself lives in the storage backend and is served by the
    authorised ``/api/v1/files/`` route; the row only names it
    (``filename`` + opaque ``file_key``), both-or-neither.
    """

    __tablename__ = "er_case_attachments"
    __table_args__ = (
        Index("ix_er_case_attachments_case_id", "case_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("er_cases.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_key: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    case = relationship("ERCase")
