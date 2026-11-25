from sqlalchemy import (
    String,
    CheckConstraint,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Identity,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base

#: Shared constraint texts (migration 0046_assets). The models and the
#: migration cannot disagree, and every name is at most 30 characters for
#: Oracle. Dialect-portable plain comparisons only.
#:
#: The asset FSM the endpoints walk: ``in_stock -> assigned -> in_stock``
#: (return, condition good), ``assigned -> maintenance`` (return, condition
#: damaged), ``assigned -> lost`` (return, condition lost),
#: ``in_stock <-> maintenance`` (explicit maintenance start/complete) and
#: ``in_stock|maintenance -> retired``. ``retired`` and ``lost`` are final.
ASSET_STATUS_CHECK = (
    "status IN ('in_stock','assigned','maintenance','retired','lost')"
)
#: An assignment is open until it is closed by a return or a transfer.
ASSIGNMENT_STATUS_CHECK = "status IN ('open','closed')"
#: Why an assignment closed: the asset came back, or it moved to someone
#: else (who must acknowledge it afresh).
ASSIGNMENT_CLOSE_REASON_CHECK = (
    "close_reason IS NULL OR close_reason IN ('returned','transferred')"
)
#: The condition recorded when an asset is returned; it decides the asset's
#: next status (good -> in_stock, damaged -> maintenance, lost -> lost).
RETURN_CONDITION_CHECK = (
    "return_condition IS NULL OR return_condition IN ('good','damaged','lost')"
)


class Asset(Base):
    """A trackable company asset (laptop, phone, badge, vehicle, ...).

    ``tag`` is the natural key and is unique **per tenant**: two tenants may
    both own ``AST-0001``; one tenant may not hold it twice. The database
    enforces ``(tenant_id, tag)`` and the service additionally refuses a
    case-insensitive duplicate inside the resolved tenant (including the
    legacy NULL-tenant rows the default tenant sees).

    ``status`` moves only through explicit endpoints — no schema exposes it
    for direct edit — and every illegal move is a ``409``.
    """

    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "tag", name="uq_assets_tenant_tag"),
        Index("ix_assets_tenant_id_id", "tenant_id", "id"),
        CheckConstraint(ASSET_STATUS_CHECK, name="ck_asset_status_fsm"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    tag: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="General")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="in_stock", nullable=False)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    assignments = relationship("AssetAssignment", back_populates="asset")


class AssetAssignment(Base):
    """One custody spell of an asset with an employee.

    At most one assignment per asset may be ``open`` at a time (enforced in
    the service inside the same transaction that opens a new one). A fresh
    assignment — including the new spell a transfer opens — starts
    unacknowledged: only the assigned employee themselves may acknowledge
    it (``acknowledged_at``), never an administrator on their behalf.

    Closing records why (``returned`` or ``transferred``) and, for a return,
    the condition the asset came back in.
    """

    __tablename__ = "asset_assignments"
    __table_args__ = (
        Index("ix_asset_asg_tenant_id_id", "tenant_id", "id"),
        CheckConstraint(ASSIGNMENT_STATUS_CHECK, name="ck_asset_asg_status"),
        CheckConstraint(ASSIGNMENT_CLOSE_REASON_CHECK, name="ck_asset_asg_close_reason"),
        CheckConstraint(RETURN_CONDITION_CHECK, name="ck_asset_asg_condition"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(10), default="open", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)
    return_condition: Mapped[str | None] = mapped_column(String(10), nullable=True)

    asset = relationship("Asset", back_populates="assignments")
    employee = relationship("Employee")