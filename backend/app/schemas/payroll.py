from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

import re

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def _validate_currency(value: str) -> str:
    """Validate an ISO 4217 currency code (uppercase, exactly 3 letters)."""
    code = value.strip().upper()
    if not _CURRENCY_RE.match(code):
        raise ValueError("currency must be a three-letter ISO 4217 code, e.g. USD")
    return code


class PayrollPeriodCreate(BaseModel):
    name: str
    start_date: date
    end_date: date
    pay_date: date
    status: str = "Draft"


class PayrollPeriodOut(PayrollPeriodCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PayComponentCreate(BaseModel):
    code: str
    name: str
    component_type: str  # Earning, Deduction, Tax
    is_taxable: bool = True
    is_pre_tax: bool = False
    is_active: bool = True


class PayComponentOut(PayComponentCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


_PT_STATES = {"KA", "MH", "TN", "TG", "WB"}

_RUN_TYPES = {"regular", "off_cycle", "adjustment", "reversal"}


class EmployeePayProfileCreate(BaseModel):
    employee_id: int
    base_salary: float = 0
    pay_frequency: str = "Monthly"
    bank_account: Optional[str] = None
    tax_withholding: float = 0
    pt_state: Optional[str] = None
    basic_pct: Optional[float] = None

    @field_validator("pt_state")
    @classmethod
    def _validate_pt_state(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        code = value.strip().upper()
        if code not in _PT_STATES:
            raise ValueError(f"pt_state must be one of {sorted(_PT_STATES)}")
        return code

    @field_validator("basic_pct")
    @classmethod
    def _validate_basic_pct(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        try:
            v = float(value)
        except Exception:
            raise ValueError("basic_pct must be a number between 0 and 100")
        if v < 0 or v > 100:
            raise ValueError("basic_pct must be between 0 and 100")
        return v


class EmployeePayProfileOut(EmployeePayProfileCreate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PayRunCreate(BaseModel):
    """Creating a pay run always starts it in Draft.

    `status` is deliberately NOT accepted here. The lifecycle
    Draft -> Processing -> Approved -> Finalized -> Paid is server-owned
    (see ALLOWED_TRANSITIONS in the payroll endpoint). Accepting a status on
    create let a client mint a run that was already `Finalized`, skipping
    calculation and approval entirely.

    `jurisdiction` names the jurisdiction whose rule pack applies to the
    run: the ISO 3166-1 alpha-2 country code the rule pack carries. It is
    required, because a run whose jurisdiction is unknown cannot be
    calculated against a verified rule, and a run that guesses one would be
    calculated against rules that may not be the ones that apply to its
    employees. The run is refused at calculation time when the pack for
    this jurisdiction is not `verified` and in force on the pay date.

    `run_type` names the pipeline kind: regular | off_cycle | adjustment |
    reversal (default regular). Adjustment/reversal runs correct a locked
    run and must name it via `reversal_of_run_id`; regular/off_cycle runs
    must not.
    """

    period_id: int
    jurisdiction: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2 country code of the jurisdiction.",
    )

    @field_validator("jurisdiction")
    @classmethod
    def _normalise_jurisdiction(cls, value: str) -> str:
        """Accept the code in either case and store it folded.

        A country code is written in upper case everywhere else; folding it
        here means the run matches the rule pack whatever the client sent.
        """
        code = value.strip().upper()
        if not code.isalpha() or len(code) != 2:
            raise ValueError(
                "jurisdiction must be a two-letter ISO 3166-1 alpha-2 country code"
            )
        return code

    currency: str = Field(
        ...,
        description="ISO 4217 currency code of the run, e.g. USD, GBP.",
    )

    @field_validator("currency")
    @classmethod
    def _normalise_currency(cls, value: str) -> str:
        return _validate_currency(value)

    run_type: Optional[str] = Field(
        default=None,
        description="Pipeline run type: regular | off_cycle | adjustment | reversal.",
    )
    reversal_of_run_id: Optional[int] = Field(
        default=None,
        description="For adjustment/reversal runs: the Finalized run being corrected.",
    )

    @field_validator("run_type")
    @classmethod
    def _validate_run_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        code = value.strip().lower()
        if code not in _RUN_TYPES:
            raise ValueError(f"run_type must be one of {sorted(_RUN_TYPES)}")
        return code


class PayRunOut(BaseModel):
    id: int
    period_id: int
    # The jurisdiction whose rule pack applies to the run, and the pack that
    # produced it once the run has been calculated. Both are None until the
    # run names a jurisdiction and is calculated.
    jurisdiction: Optional[str] = None
    rule_pack_id: Optional[str] = None
    #: Pipeline run type (regular default) + reversal link for corrections.
    run_type: Optional[str] = None
    reversal_of_run_id: Optional[int] = None
    status: str
    total_gross: float
    total_deductions: float
    total_net: float
    headcount: int
    run_date: Optional[datetime] = None
    processed_by: Optional[int] = None
    processed_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    finalized_by: Optional[int] = None
    finalized_at: Optional[datetime] = None
    warning: Optional[str] = None
    created_at: Optional[datetime] = None
    #: ISO 4217 currency code of the run. Backfilled to the tenant default
    #: on migration 0027_payroll_currency.
    currency: Optional[str] = None

    class Config:
        from_attributes = True


class PaySlipCreate(BaseModel):
    pay_run_id: int
    employee_id: int
    gross_pay: float = 0
    net_pay: float = 0
    total_deductions: float = 0
    earnings_json: Optional[str] = None
    deductions_json: Optional[str] = None
    # `status` is server-owned; see PayRunCreate.


class PaySlipOut(BaseModel):
    id: int
    pay_run_id: int
    employee_id: int
    gross_pay: float = 0
    net_pay: float = 0
    total_deductions: float = 0
    # The statutory contributions the rule pack computed. They are null on a
    # payslip written before the columns existed.
    employee_contributions: Optional[float] = None
    employer_contributions: Optional[float] = None
    earnings_json: Optional[str] = None
    deductions_json: Optional[str] = None
    # The approved time and leave the slip was calculated from, including the
    # entries that were not approved and therefore excluded. Null on a slip
    # written before the column existed.
    inputs_json: Optional[str] = None
    status: str = "Draft"
    created_at: Optional[datetime] = None
    #: ISO 4217 currency code of the payslip. Matches the pay run's currency.
    currency: Optional[str] = None

    class Config:
        from_attributes = True
