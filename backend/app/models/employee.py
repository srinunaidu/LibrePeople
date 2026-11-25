from sqlalchemy import (
    String,
    Boolean,
    Integer,
    Numeric,
    Date,
    DateTime,
    ForeignKey,
    Text,
    Identity,
    Index,
    CheckConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base

#: India payroll identity checks (india-payroll slice 1). One text has to
#: compile on SQLite (the test suites) *and* on Oracle (production), so the
#: patterns are written as plain ``length`` / ``substr`` / ``BETWEEN``
#: expressions rather than dialect-specific ones: ``regexp_like`` does not
#: exist on SQLite and ``GLOB`` does not exist on Oracle. Migration
#: ``0030_india_employee_fields`` imports these constants, so the models and
#: the migration cannot disagree.
#: PAN: ``^[A-Z]{5}[0-9]{4}[A-Z]$``.
PAN_NUMBER_CHECK = (
    "pan_number IS NULL OR (length(pan_number) = 10 "
    "AND substr(pan_number,1,1) BETWEEN 'A' AND 'Z' "
    "AND substr(pan_number,2,1) BETWEEN 'A' AND 'Z' "
    "AND substr(pan_number,3,1) BETWEEN 'A' AND 'Z' "
    "AND substr(pan_number,4,1) BETWEEN 'A' AND 'Z' "
    "AND substr(pan_number,5,1) BETWEEN 'A' AND 'Z' "
    "AND substr(pan_number,6,1) BETWEEN '0' AND '9' "
    "AND substr(pan_number,7,1) BETWEEN '0' AND '9' "
    "AND substr(pan_number,8,1) BETWEEN '0' AND '9' "
    "AND substr(pan_number,9,1) BETWEEN '0' AND '9' "
    "AND substr(pan_number,10,1) BETWEEN 'A' AND 'Z')"
)
#: New (§115BAC) or old regime; the accepted decision is new-regime only.
TAX_REGIME_CHECK = "tax_regime IN ('new','old')"

#: NFR-014 safe constraint C11 (migration 0043_integrity_expand). Shared
#: text so the model and the migration cannot disagree; the name is at
#: most 30 characters for Oracle. An open row carries NULL; a closed row
#: stops on or after the day it started.
EMPHIST_DATES_CHECK = "effective_to IS NULL OR effective_to >= effective_from"
#: IFSC: ``^[A-Z]{4}0[A-Z0-9]{6}$`` — the fifth character is the literal 0.
IFSC_CODE_CHECK = (
    "ifsc_code IS NULL OR (length(ifsc_code) = 11 "
    "AND substr(ifsc_code,1,1) BETWEEN 'A' AND 'Z' "
    "AND substr(ifsc_code,2,1) BETWEEN 'A' AND 'Z' "
    "AND substr(ifsc_code,3,1) BETWEEN 'A' AND 'Z' "
    "AND substr(ifsc_code,4,1) BETWEEN 'A' AND 'Z' "
    "AND substr(ifsc_code,5,1) = '0' "
    "AND (substr(ifsc_code,6,1) BETWEEN '0' AND '9' "
    "     OR substr(ifsc_code,6,1) BETWEEN 'A' AND 'Z') "
    "AND (substr(ifsc_code,7,1) BETWEEN '0' AND '9' "
    "     OR substr(ifsc_code,7,1) BETWEEN 'A' AND 'Z') "
    "AND (substr(ifsc_code,8,1) BETWEEN '0' AND '9' "
    "     OR substr(ifsc_code,8,1) BETWEEN 'A' AND 'Z') "
    "AND (substr(ifsc_code,9,1) BETWEEN '0' AND '9' "
    "     OR substr(ifsc_code,9,1) BETWEEN 'A' AND 'Z') "
    "AND (substr(ifsc_code,10,1) BETWEEN '0' AND '9' "
    "     OR substr(ifsc_code,10,1) BETWEEN 'A' AND 'Z') "
    "AND (substr(ifsc_code,11,1) BETWEEN '0' AND '9' "
    "     OR substr(ifsc_code,11,1) BETWEEN 'A' AND 'Z'))"
)


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (Index("ix_employees_tenant_id_id", "tenant_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    hire_date: Mapped[Date] = mapped_column(Date, nullable=False)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("jobs.id"), nullable=False)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id"), nullable=False)
    #: The legal entity employing this person (LP-CORE-003/010). Nullable so
    #: rows written before the entity existed stay readable; the create and
    #: update paths validate the reference when one is supplied.
    #:
    #: The foreign key lives in migration 0036, not here: the frozen
    #: baseline builds this table from the current models, and an inline
    #: reference to a table a later revision creates would leave a fresh
    #: database with a dangling reference that an old batch migration
    #: cannot reflect past (0018). The join is spelled out on the
    #: relationship instead.
    legal_entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    manager_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("employees.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Active")  # Active, On Leave, Terminated, Rehired
    #: Full-time / Part-time / Contract / Intern. Nullable so rows written
    #: before the employment record existed stay readable; the create path
    #: and the employment editor set it.
    employment_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    #: Set when the employee moves to `Terminated`, cleared by `Rehired`.
    termination_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    salary: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    # --- India payroll (india-payroll slice 1) --------------------------
    # Nullable throughout: only an Indian tenant's employees carry them, and
    # every other jurisdiction must be able to leave them empty.
    #: Permanent Account Number, `^[A-Z]{5}[0-9]{4}[A-Z]$`. The CHECK text is
    #: :data:`PAN_NUMBER_CHECK` (dialect-portable; see its comment).
    pan_number: Mapped[str | None] = mapped_column(
        String(10),
        CheckConstraint(PAN_NUMBER_CHECK, name="ck_employees_pan_number"),
        nullable=True,
    )
    #: New (§115BAC) or old regime. NOT NULL with a server default because
    #: the accepted decision is new-regime only, so every row — including
    #: rows that predate the column — reads back as `new`.
    tax_regime: Mapped[str] = mapped_column(
        String(10),
        CheckConstraint(TAX_REGIME_CHECK, name="ck_employees_tax_regime"),
        nullable=False,
        server_default=text("'new'"),
        default="new",
    )
    #: Employees' Provident Fund Universal Account Number (12 digits).
    pf_uan: Mapped[str | None] = mapped_column(String(12), nullable=True)
    #: Employees' State Insurance registration number.
    esi_number: Mapped[str | None] = mapped_column(String(17), nullable=True)
    #: Indian Financial System Code of the bank branch, `^[A-Z]{4}0[A-Z0-9]{6}$`.
    ifsc_code: Mapped[str | None] = mapped_column(
        String(11),
        CheckConstraint(IFSC_CODE_CHECK, name="ck_employees_ifsc_code"),
        nullable=True,
    )
    # --- India aadhaar (india-payroll slice 6) -------------------------
    # Encrypted at rest via app.core.encryption (Fernet/AES). Raw Aadhaar is
    # never stored in clear; the last 4 are kept separately for masked display.
    aadhaar_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    aadhaar_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    aadhaar_masked: Mapped[str | None] = mapped_column(String(14), nullable=True)
    pan_verified_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    uan_verified_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    esi_verified_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    form11_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    nominee_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def aadhaar_number(self) -> str | None:
        """Decrypt aadhaar on access (server-side only). Returns None if absent."""
        if not self.aadhaar_encrypted:
            return None
        try:
            from app.core.encryption import decrypt_field
            return decrypt_field(self.aadhaar_encrypted)
        except Exception:
            return None

    @aadhaar_number.setter
    def aadhaar_number(self, value: str | None) -> None:
        """Encrypt and store Aadhaar, populating last4/masked."""
        if not value:
            self.aadhaar_encrypted = None
            self.aadhaar_last4 = None
            self.aadhaar_masked = None
            return
        import re
        from app.core.encryption import encrypt_field, aadhaar_last4 as _last4, mask_aadhaar
        digits = re.sub(r"\D", "", str(value))
        # Store last4 and masked even if not 12-digit (validation is elsewhere)
        self.aadhaar_encrypted = encrypt_field(digits if len(digits) == 12 else str(value))
        self.aadhaar_last4 = _last4(digits if len(digits)==12 else str(value)) or (digits[-4:] if len(digits)>=4 else None)
        self.aadhaar_masked = mask_aadhaar(digits if len(digits)==12 else str(value))

    @property
    def aadhaar_display(self) -> str | None:
        """Masked display: ****-****-1234. Never raw."""
        if self.aadhaar_masked:
            return self.aadhaar_masked
        if self.aadhaar_last4:
            return f"****-****-{self.aadhaar_last4}"
        return None

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job = relationship("Job", back_populates="employees")
    department = relationship("Department", back_populates="employees")
    legal_entity = relationship(
        "LegalEntity",
        primaryjoin="Employee.legal_entity_id == LegalEntity.id",
        foreign_keys="Employee.legal_entity_id",
        back_populates="employees",
    )
    manager = relationship("Employee", remote_side=[id], back_populates="reports")
    reports = relationship("Employee", back_populates="manager")
    history = relationship(
        "EmployeeHistory",
        back_populates="employee",
        order_by="EmployeeHistory.id",
    )


class EmployeeHistory(Base):
    """One effective dated change to an employee's employment record.

    History is **append only**. A change never rewrites an earlier row: it
    closes the previous open row for the same field with an ``effective_to``
    date (exclusive) and appends a new row. The pair of dates therefore says
    which value was in force on any day, and an edited or deleted row would
    break that story.
    """

    __tablename__ = "employee_history"
    __table_args__ = (
        Index("ix_employee_history_tenant_id_id", "tenant_id", "id"),
        CheckConstraint(EMPHIST_DATES_CHECK, name="ck_emphist_dates"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id"), nullable=False, index=True
    )
    field: Mapped[str] = mapped_column(String(40), nullable=False)
    previous_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: First day the new value was in force.
    effective_from: Mapped[Date] = mapped_column(Date, nullable=False)
    #: First day it stopped being in force. Null means "still in force".
    effective_to: Mapped[Date | None] = mapped_column(Date, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    changed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    changed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    employee = relationship("Employee", back_populates="history")
