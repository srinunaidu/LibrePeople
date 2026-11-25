from sqlalchemy import (
    String,
    Boolean,
    CheckConstraint,
    Integer,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    Text,
    Identity,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base

#: NFR-014 safe constraints (migration 0043_integrity_expand). The SQL
#: texts are shared with the migration — the models and the migration
#: cannot disagree — and every name is at most 30 characters for Oracle.
#: Dialect-portable plain comparisons: no regexp_like, no GLOB.
#: C4: money is never negative.
CLAIM_AMOUNT_CHECK = "amount >= 0"
#: C5: the claim FSM the expenses endpoint walks.
CLAIM_STATUS_CHECK = (
    "status IN ('DRAFT','SUBMITTED','L1_APPROVED','APPROVED','REJECTED')"
)
#: C6: payment is orthogonal to approval and moves only UNPAID -> PAID.
CLAIM_PAYSTAT_CHECK = "payment_status IN ('UNPAID','PAID')"
#: C13: a receipt's byte size is metadata and never negative.
RECEIPT_SIZE_CHECK = "size_bytes >= 0"


class ExpenseCategory(Base):
    """A reimbursable expense category (Travel, Meals, Lodging, ...).

    LP-EXP-001: the category master the claim form offers. ``code`` is the
    unique natural key (``EXP-`` household when auto-generated), ``is_active``
    archives a category the form should stop offering. Deletion is a
    deactivate, never a row removal: claims keep the category they were
    filed under.
    """

    __tablename__ = "expense_categories"
    __table_args__ = (
        Index("ix_expense_categories_tenant_id_id", "tenant_id", "id"),
        # Tenant-scoped natural key: the same code may exist in two
        # tenants, but never twice in one. The app check is
        # case-insensitive and treats NULL tenant as the legacy default;
        # this composite is the DB backstop for non-NULL tenants (NULL
        # never equals NULL, so the app check remains authoritative).
        # Name kept short for Oracle's 30-char identifier limit.
        UniqueConstraint("tenant_id", "code", name="uq_exp_cat_tenant_code"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExpenseClaim(Base):
    """An employee's request for reimbursement of one expense.

    LP-EXP-001/002: money, so every amount is ``Numeric(12, 2)`` and every
    state change passes through an explicit endpoint — clients cannot set
    ``status`` or ``payment_status`` directly.

    Claim state: ``DRAFT -> SUBMITTED -> L1_APPROVED -> APPROVED`` with
    ``REJECTED`` out of ``SUBMITTED``/``L1_APPROVED`` and back to ``DRAFT``
    for rework. Payment state is orthogonal: ``UNPAID -> PAID`` via an
    explicit mark-paid on an ``APPROVED`` claim, never as a status move.
    """

    __tablename__ = "expense_claims"
    __table_args__ = (
        Index("ix_expense_claims_tenant_id_id", "tenant_id", "id"),
        CheckConstraint(CLAIM_AMOUNT_CHECK, name="ck_claim_amount_nonneg"),
        CheckConstraint(CLAIM_STATUS_CHECK, name="ck_claim_status_fsm"),
        CheckConstraint(CLAIM_PAYSTAT_CHECK, name="ck_claim_paystat_fsm"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("expense_categories.id"), nullable=False, index=True)
    expense_date: Mapped[Date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    payment_status: Mapped[str] = mapped_column(String(10), default="UNPAID")
    submitted_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    l1_approved_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    l1_approved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    paid_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("Employee")
    category = relationship("ExpenseCategory")


class ExpenseReceipt(Base):
    """A receipt file attached to an expense claim.

    LP-EXP-002: the bytes live in object storage under an opaque key
    (``expenses/<claim>/<uuid><ext>``) — no employee name, no amount, no
    claim id guessability beyond the claim itself. The row stores the key,
    never a signed URL: downloads go through the authenticated
    ``GET /api/v1/files/{key}`` route, so an unauthenticated caller learns
    nothing from a receipt id.
    """

    __tablename__ = "expense_receipts"
    __table_args__ = (
        Index("ix_expense_receipts_tenant_id_id", "tenant_id", "id"),
        CheckConstraint(RECEIPT_SIZE_CHECK, name="ck_receipt_size_nonneg"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    claim_id: Mapped[int] = mapped_column(Integer, ForeignKey("expense_claims.id"), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    claim = relationship("ExpenseClaim")
