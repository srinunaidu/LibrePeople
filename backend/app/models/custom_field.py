"""Configurable employee fields (LP-CORE-005).

A tenant declares its own employee attributes — ``CustomFieldDef`` — and
each employee carries one value per definition — ``CustomFieldValue``.
Values are stored as text and coerced by
:mod:`app.services.custom_fields`, so a new type never means a new
column: the schema stays fixed while the tenant's vocabulary grows.

Visibility
----------
``visibility`` is ``all`` (anyone who may view the employee sees it) or
``hr_only`` (only ``HR``/``SuperAdmin``). ``is_sensitive`` keeps the key
visible but masks the value to ``None`` for other roles, mirroring
:mod:`app.core.sensitive_fields`. Personal values must never leak through
a directory read, an export, or a row-error message.
"""
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

#: Field types the service knows how to validate and coerce.
FIELD_TYPES = ("text", "number", "integer", "date", "boolean", "email")

#: Who may see the definition's values.
VISIBILITIES = ("all", "hr_only")


class CustomFieldDef(Base):
    """One tenant-configured employee attribute (LP-CORE-005)."""

    __tablename__ = "custom_field_defs"
    __table_args__ = (
        Index("ix_cfdef_tenant_id_id", "tenant_id", "id"),
        # Tenant-scoped natural key: the same key may exist in two
        # tenants, but never twice in one. The app check is
        # case-insensitive and treats NULL tenant as the legacy default;
        # this composite is the DB backstop for non-NULL tenants (NULL
        # never equals NULL, so the app check remains authoritative).
        # Name kept short for Oracle's 30-char identifier limit.
        UniqueConstraint("tenant_id", "key", name="uq_cfdef_tenant_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    #: Machine key, e.g. ``tshirt_size``. Imported/exported as
    #: ``custom.<key>`` (lowercased).
    key: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    #: One of :data:`FIELD_TYPES`.
    field_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: Personal values are masked to ``None`` for non-HR roles.
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: One of :data:`VISIBILITIES`. ``hr_only`` omits the key entirely
    #: for non-HR roles.
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="all")
    #: JSON-encoded options for a closed vocabulary (future ``enum``
    #: type). Null means free input.
    options_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    values = relationship(
        "CustomFieldValue",
        back_populates="definition",
        cascade="all, delete-orphan",
    )


class CustomFieldValue(Base):
    """One employee's value for one definition (LP-CORE-005).

    The value is stored as text; :mod:`app.services.custom_fields`
    coerces it on read and write. One row per (employee, definition).
    """

    __tablename__ = "custom_field_values"
    __table_args__ = (
        Index("ix_cfval_tenant_id_id", "tenant_id", "id"),
        Index("ix_cfval_employee_id", "employee_id"),
        # One value per employee per definition. Name kept short for
        # Oracle's 30-char identifier limit.
        UniqueConstraint("employee_id", "def_id", name="uq_cfval_emp_def"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id"), nullable=False
    )
    def_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("custom_field_defs.id"), nullable=False
    )
    #: The coerced value, always stored as text (ISO 8601 for dates,
    #: canonical spelling for booleans/numbers).
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    definition = relationship("CustomFieldDef", back_populates="values")
