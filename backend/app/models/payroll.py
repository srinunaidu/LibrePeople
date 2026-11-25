from decimal import Decimal

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
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base

#: Professional-tax states the India rule pack carries a PT table for
#: (india-payroll slice 1). Dialect-portable plain CHECK — one text compiles
#: on SQLite and on Oracle (see app.models.employee for why not GLOB /
#: regexp_like). Migration ``0030_india_employee_fields`` imports this, so
#: the models and the migration cannot disagree.
PT_STATE_CHECK = "pt_state IN ('KA','MH','TN','TG','WB')"

#: NFR-014 safe constraint C12 (migration 0043_integrity_expand). Shared
#: text so the model and the migration cannot disagree; the name is at
#: most 30 characters for Oracle. Payslip money is never negative.
PAYSLIP_AMOUNTS_CHECK = (
    "gross_pay >= 0 AND net_pay >= 0 AND total_deductions >= 0"
)

#: Basic+DA proportion of gross for India payroll (slice 5). Nullable so
#: every row that predates the column stays readable; CHECK 0..100 mirrors
#: migration ``0031_india_fnf_basic_da`` and the Pydantic validation.
BASIC_PCT_CHECK = "basic_pct IS NULL OR (basic_pct >= 0 AND basic_pct <= 100)"


#: Pay-run pipeline type (payroll pipeline mechanics). Expand-only nullable:
#: every row that predates the column reads as ``regular``. CHECK mirrors
#: migration ``0045_payroll_pipeline_run_type``.
RUN_TYPE_CHECK = (
    "run_type IS NULL OR run_type IN "
    "('regular','off_cycle','adjustment','reversal')"
)

#: Valid run_type values accepted by the API.
RUN_TYPES = ("regular", "off_cycle", "adjustment", "reversal")


class PayrollPeriod(Base):
    """A payroll cycle (e.g. monthly)."""

    __tablename__ = "payroll_periods"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Date] = mapped_column(Date, nullable=False)
    pay_date: Mapped[Date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Draft")  # Draft, Processing, Approved, Paid
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PayComponent(Base):
    """A reusable earning/deduction/tax component."""

    __tablename__ = "pay_components"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    component_type: Mapped[str] = mapped_column(String(20), nullable=False)  # Earning, Deduction, Tax
    is_taxable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_pre_tax: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmployeePayProfile(Base):
    """Pay configuration for an employee."""

    __tablename__ = "employee_pay_profiles"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False, unique=True)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    pay_frequency: Mapped[str] = mapped_column(String(20), default="Monthly")  # Monthly, Biweekly, Weekly
    bank_account: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # percent fallback; ignored by packs that carry a banded tax table (e.g. IN)
    tax_withholding: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    #: Professional-tax state the employee pays in: KA, MH, TN, TG or WB
    #: (india-payroll slice 1). Nullable: only Indian tenants name one. The
    #: rule pack for IN carries one PT table per state (`pt_ka`, ...); the
    #: engine picks the table named by this code.
    pt_state: Mapped[str | None] = mapped_column(
        String(2),
        CheckConstraint(PT_STATE_CHECK, name="ck_employee_pay_profiles_pt_state"),
        nullable=True,
    )
    #: Basic+DA proportion of gross, 0..100. When present PF is computed on
    #: Basic+DA (= gross × basic_pct/100) instead of full gross; ESI stays on
    #: gross. Nullable — only Indian profiles that have a Basic/DA split use it.
    basic_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        CheckConstraint(BASIC_PCT_CHECK, name="ck_employee_pay_profiles_basic_pct"),
        nullable=True,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee = relationship("Employee")


class PayRun(Base):
    """A single payroll run for a period."""

    __tablename__ = "pay_runs"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    period_id: Mapped[int] = mapped_column(Integer, ForeignKey("payroll_periods.id"), nullable=False)
    # The jurisdiction whose rule pack applies to this run. The country code
    # is the ISO 3166-1 alpha-2 code the rule pack carries; the rule pack
    # of that jurisdiction, in force on the pay date and in state
    # `verified`, is the only thing this run may be calculated from.
    #
    # The column is nullable because the migration that introduced it is the
    # expand half of an expand-then-contract change: a run that existed
    # before the jurisdiction was recorded cannot name one, and such a run
    # is refused rather than calculated against a guess. The contract half
    # (NOT NULL) comes after every deployment records a jurisdiction.
    jurisdiction: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # The pack that produced this run, recorded once the run is calculated.
    rule_pack_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    #: Pipeline run type: regular | off_cycle | adjustment | reversal.
    #: Nullable expand-only (see 0045); missing reads as ``regular``.
    run_type: Mapped[str | None] = mapped_column(
        String(20),
        CheckConstraint(RUN_TYPE_CHECK, name="ck_pay_runs_run_type"),
        nullable=True,
    )
    #: Self-reference to the Finalized run an adjustment/reversal corrects.
    #: Nullable expand-only; the API validates the link. No DB-level FK so
    #: SQLite batch rebuilds can drop the column (the ORM never joins on it).
    reversal_of_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Draft -> Processing -> Approved -> Finalized -> Paid (see ALLOWED_TRANSITIONS)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    total_gross: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_net: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    headcount: Mapped[int] = mapped_column(Integer, default=0)
    #: ISO 4217 currency code of the run (e.g. USD, GBP). Every pay figure
    #: on the run is denominated in this currency. Nullable during the
    #: expand-then-contract window; backfilled to the tenant default on
    #: migration 0027_payroll_currency.
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    run_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Segregation of duties + traceability: who processed, approved and locked.
    processed_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    processed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    finalized_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Operator-facing note, e.g. employees excluded because they were inactive.
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    period = relationship("PayrollPeriod")


class PaySlip(Base):
    """A payslip for one employee in one pay run."""

    __tablename__ = "pay_slips"
    __table_args__ = (
        # One payslip per employee per run. This is the database-level backstop
        # against a retried or concurrent process creating duplicates.
        UniqueConstraint("pay_run_id", "employee_id", name="uq_payslip_run_employee"),
        CheckConstraint(PAYSLIP_AMOUNTS_CHECK, name="ck_payslip_amounts_nonneg"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    pay_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("pay_runs.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    #: ISO 4217 currency code of the payslip. Matches the pay run's currency.
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    # The statutory contributions the rule pack computed for this payslip.
    #
    # The employee's contributions are the employee's own money inside the
    # deductions; the employer's are the employer's money and are not part
    # of the employee's pay at all. The employer column exists because the
    # pack computes the contribution and the payslip had nowhere to put it:
    # without a column of its own it was lost the moment the payslip was
    # written, and the reconciliation had nothing to check.
    #
    # Both are nullable because the migration that introduced them is the
    # expand half of an expand-then-contract change: a payslip written
    # before the columns existed carries no contribution, and the
    # reconciliation reads a missing total as zero.
    employee_contributions: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    employer_contributions: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    earnings_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    deductions_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    # The approved time and leave the slip was calculated from, recorded so
    # the figure can be traced back to the rows that justified it. A payslip
    # that cannot name its inputs is a figure nobody can audit. Nullable
    # because slips written before this column existed carry none.
    inputs_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON object
    status: Mapped[str] = mapped_column(String(20), default="Draft")  # Draft, Paid
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pay_run = relationship("PayRun")
    employee = relationship("Employee")
