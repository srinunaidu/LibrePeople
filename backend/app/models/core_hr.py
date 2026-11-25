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
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base


class Location(Base):
    """A physical work location / site."""

    __tablename__ = "locations"
    __table_args__ = (Index("ix_locations_tenant_id_id", "tenant_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    timezone: Mapped[str] = mapped_column(String(60), default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CostCenter(Base):
    """A cost center for financial tracking."""

    __tablename__ = "cost_centers"
    __table_args__ = (Index("ix_cost_centers_tenant_id_id", "tenant_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    department_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    department = relationship("Department")


class Position(Base):
    """A position (slot) within an org structure, distinct from a job profile."""

    __tablename__ = "positions"
    __table_args__ = (Index("ix_positions_tenant_id_id", "tenant_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=False)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id"), nullable=False)
    location_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("locations.id"), nullable=True)
    reports_to_position_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("positions.id"), nullable=True)
    fte: Mapped[float] = mapped_column(Numeric(4, 2), default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job")
    department = relationship("Department")
    location = relationship("Location")


class LegalEntity(Base):
    """A legal entity (employer of record) within the customer's installation.

    LP-CORE-003/010: one installation holds many legal entities, and an
    employee belongs to at most one of them (``employees.legal_entity_id``,
    nullable). The entity carries only the identity the organisation masters
    need — code, name, country, registration number, address — and an
    ``is_active`` flag. Deletion is a soft-deactivate: the row stays so that
    employees hired under it keep their history. No custom fields, no
    payroll state.
    """

    __tablename__ = "legal_entities"
    __table_args__ = (
        Index("ix_legal_entities_tenant_id_id", "tenant_id", "id"),
        # Tenant-scoped natural key: the same code may exist in two
        # tenants, but never twice in one. The app check is
        # case-insensitive and treats NULL tenant as the legacy default;
        # this composite is the DB backstop for non-NULL tenants (NULL
        # never equals NULL, so the app check remains authoritative).
        # Name kept short for Oracle's 30-char identifier limit.
        UniqueConstraint("tenant_id", "code", name="uq_le_tenant_code"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(60), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employees = relationship(
        "Employee",
        primaryjoin="LegalEntity.id == Employee.legal_entity_id",
        foreign_keys="Employee.legal_entity_id",
        back_populates="legal_entity",
    )


class EmployeeDocument(Base):
    """A document in an employee's file (beyond onboarding).

    LP-DOC-002: a document is versioned. Each upload appends a
    :class:`DocumentVersion` row and bumps ``current_version``; the rows
    behind it are the download history. ``storage_key`` is the opaque key
    inside the storage backend (the ``/api/v1/files/`` route serves it to
    an authenticated account, and each download is recorded in
    :class:`DocumentAccessLog`). ``retention_until`` bounds how long the
    document is kept once it is Expired: the retention sweep deletes only
    Expired documents past this date, never Active or Archived ones.
    """

    __tablename__ = "employee_documents"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(60), nullable=False)  # Contract, ID, Tax, Certificate, Policy, Other
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_url: Mapped[str] = mapped_column(String(500), nullable=False)
    #: Opaque key inside the storage backend (LP-DOC-002). Older rows carry
    #: only ``storage_url``; the key is derived from it on first touch.
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    #: The newest version number (LP-DOC-002). Starts at 1 with the first
    #: upload; every further upload bumps it by one.
    current_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    #: Keep-until date once the document is Expired (LP-DOC-002). The purge
    #: deletes only Expired documents on or past this date.
    retention_until: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Active")  # Active, Archived, Expired
    expiry_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee")
    versions = relationship(
        "DocumentVersion",
        primaryjoin="DocumentVersion.document_id == EmployeeDocument.id",
        foreign_keys="DocumentVersion.document_id",
        order_by="DocumentVersion.version_no",
    )


class DocumentVersion(Base):
    """One immutable upload in a document's history (LP-DOC-002).

    The newest upload is the document's content; the older rows are the
    history, kept so that what an employee saw and acknowledged can be
    reconstructed. Rows are never updated, only appended — and removed by
    the retention purge together with their document.
    """

    __tablename__ = "document_versions"
    __table_args__ = (
        Index("ix_docver_doc_id", "document_id"),
        UniqueConstraint("document_id", "version_no", name="uq_docver_doc_ver"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employee_documents.id"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    storage_url: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentAck(Base):
    """An employee's acknowledgement of a document (LP-DOC-002).

    Written once per (document, employee): a second acknowledgement by the
    same account is refused with 409, so "I have read this" stays a single
    accountable event rather than a counter that can be pumped.
    """

    __tablename__ = "document_acks"
    __table_args__ = (
        Index("ix_docack_doc_id", "document_id"),
        UniqueConstraint(
            "document_id", "acknowledged_by", name="uq_docack_doc_user"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employee_documents.id"), nullable=False
    )
    acknowledged_by: Mapped[str] = mapped_column(String(100), nullable=False)
    acknowledged_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DocumentAccessLog(Base):
    """One authenticated download of a document (LP-DOC-002).

    Appended by the ``GET /api/v1/files/{path}`` route whenever the key it
    serves belongs to an employee document. Who read what, and when.
    """

    __tablename__ = "document_access_logs"
    __table_args__ = (Index("ix_doclog_doc_id", "document_id"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employee_documents.id"), nullable=False
    )
    accessed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    accessed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class HRCase(Base):
    """An HR service request / ticket (case management).

    A case comes from two doors. One is HR's own queue, and those cases
    carry an employee, a category and a priority. The other is the public
    contact form, which no one is signed in to and which therefore has no
    employee, no category and no priority: those cases arrive with
    ``status = "Intake"`` and ``source = "public_contact"``, and they hold
    the sender's name in the subject, the sender's address in
    ``sender_email`` and the message itself in ``message``.

    The intake state is a state of its own so that a message from the web
    is never mistaken for a case about an employee, and so that the queue
    can pick the two apart at a glance.
    """

    __tablename__ = "hr_cases"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    employee_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="General")  # Payroll, Benefits, IT, Facilities, Policy, General
    priority: Mapped[str] = mapped_column(String(20), default="Medium")  # Low, Medium, High, Urgent
    status: Mapped[str] = mapped_column(String(20), default="Open")  # Open, InProgress, Resolved, Closed, Intake
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sla_due: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Where the case came from. "hr" for the cases HR opens itself,
    # "public_contact" for the ones the public form sends.
    source: Mapped[str] = mapped_column(
        String(40), server_default="hr", default="hr", nullable=False, index=True
    )
    # The sender's address and message, for a case that came from the
    # public form. Both are null for a case HR opened itself.
    sender_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employee = relationship("Employee")


class CaseComment(Base):
    """A comment on an HR case.

    LP-SVC-001/003: comments are append-only — the API offers no update or
    delete for them, so the rows behind a case are its ordered history.
    A comment may carry one attachment, named by ``attachment_filename``
    with its opaque key in ``attachment_key`` (the key served by the
    authorised ``/api/v1/files/`` route). Both columns are nullable and
    both-or-neither: a comment with no attachment carries neither.
    """

    __tablename__ = "case_comments"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("hr_cases.id"), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    #: The attachment's file name (LP-SVC-001). Null when the comment
    #: carries no attachment.
    attachment_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: The attachment's opaque key inside the storage backend
    #: (LP-SVC-001). Null when the comment carries no attachment.
    attachment_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case = relationship("HRCase")
