from pydantic import BaseModel, EmailStr
from typing import Any, Optional
from datetime import date, datetime

from app.schemas.pagination import PageMeta


class EmployeeBase(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    hire_date: date
    job_id: int
    department_id: int
    manager_id: Optional[int] = None
    #: The legal entity employing this person (LP-CORE-003/010). Nullable:
    #: an employee need not belong to one.
    legal_entity_id: Optional[int] = None
    status: str = "Active"
    employment_type: Optional[str] = None
    salary: Optional[float] = None
    # --- India payroll (india-payroll slice 1) ---------------------------
    # Optional fields only, so no existing caller breaks. `tax_regime`
    # defaults to `new`: the accepted decision is new-regime (§115BAC) only,
    # and the database column is NOT NULL with the same server default.
    #: Permanent Account Number, `^[A-Z]{5}[0-9]{4}[A-Z]$` (enforced by the
    #: database CHECK `ck_employees_pan_number`).
    pan_number: Optional[str] = None
    tax_regime: str = "new"
    #: Employees' Provident Fund Universal Account Number.
    pf_uan: Optional[str] = None
    #: Employees' State Insurance registration number.
    esi_number: Optional[str] = None
    #: Bank-branch IFSC code, `^[A-Z]{4}0[A-Z0-9]{6}$` (CHECK
    #: `ck_employees_ifsc_code`).
    ifsc_code: Optional[str] = None
    # --- India identity slice 6 ---
    aadhaar_number: Optional[str] = None  # 12-digit, stored encrypted, masked on read
    pan_verified_status: Optional[str] = None
    uan_verified_status: Optional[str] = None
    esi_verified_status: Optional[str] = None
    form11_json: Optional[str] = None
    nominee_json: Optional[str] = None
    #: Configurable attributes (LP-CORE-005): ``{"tshirt_size": "M"}``.
    #: Keys are definition keys (case-insensitive); unknown keys and values
    #: that fail the definition's type are refused with 422.
    custom_fields: Optional[dict[str, Any]] = None


class EmployeeCreate(EmployeeBase):
    """Create a directory record.

    `employee_id` is optional: when omitted the endpoint auto-generates the
    next free identifier in the EMP-0007 household (`app/core/ids.py`).
    """

    employee_id: Optional[str] = None


class EmployeeUpdate(BaseModel):
    """A partial change to the employment record.

    The fields that describe employment (status, employment type, job,
    department, manager, salary) are effective-dated: the change applies now
    and a history row records it. A future `effective_from` is refused
    because nothing would apply it.
    """

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    hire_date: Optional[date] = None
    job_id: Optional[int] = None
    department_id: Optional[int] = None
    manager_id: Optional[int] = None
    #: Reassign the employee to another legal entity, or clear it with null.
    legal_entity_id: Optional[int] = None
    status: Optional[str] = None
    employment_type: Optional[str] = None
    salary: Optional[float] = None
    #: First day the change is in force. Defaults to today; a future date is
    #: refused.
    effective_from: Optional[date] = None
    #: Why the change was made. Stored on every history row it produces.
    reason: Optional[str] = None
    #: Configurable attributes (LP-CORE-005). Same validation as create.
    custom_fields: Optional[dict[str, Any]] = None


#: The employment statuses the deployment stores. The import contract, the
#: People screen and the list filter all speak this vocabulary. It is exported
#: so the filter and the contract cannot drift from the data.
EMPLOYEE_STATUSES = ("Active", "On Leave", "Terminated", "Rehired")


class EmployeeOut(EmployeeBase):
    #: What is **stored**, not what would be accepted today. The input models
    #: validate `EmailStr`; the output does not, because a response must never
    #: fail on a value the database already holds. A row written by a seed, an
    #: import or an older version of the rules took `GET /employees/` down with
    #: a `ResponseValidationError` — one row, the whole list, 500 for every
    #: caller. The address is data; rendering it is not the place to police it.
    email: str
    id: int
    termination_date: Optional[date] = None
    created_at: Optional[datetime] = None
    # --- India payroll (india-payroll slice 1) ---------------------------
    pan_number: Optional[str] = None
    tax_regime: Optional[str] = None
    pf_uan: Optional[str] = None
    esi_number: Optional[str] = None
    ifsc_code: Optional[str] = None

    class Config:
        from_attributes = True


class EmployeeHistoryOut(BaseModel):
    """One effective-dated row of the employment history."""

    id: int
    field: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    effective_from: date
    effective_to: Optional[date] = None
    reason: Optional[str] = None
    changed_by: Optional[str] = None
    changed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmployeePage(BaseModel):
    """One page of the employee directory (contract: `PaginatedEmployees`)."""

    items: list[EmployeeOut]
    meta: PageMeta


class DepartmentBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool = True


class DepartmentCreate(DepartmentBase):
    """`code` optional — auto-generated (DEP-0007) when omitted."""

    code: Optional[str] = None


class DepartmentUpdate(BaseModel):
    """A partial edit of a department. Only the fields sent are changed."""

    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentOut(DepartmentBase):
    id: int

    class Config:
        from_attributes = True


class JobBase(BaseModel):
    title: str
    code: str
    department_id: int
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    is_active: bool = True


class JobCreate(JobBase):
    """`code` optional — auto-generated (JOB-0007) when omitted."""

    code: Optional[str] = None


class JobUpdate(BaseModel):
    """A partial edit of a job. Only the fields sent are changed."""

    title: Optional[str] = None
    code: Optional[str] = None
    department_id: Optional[int] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    is_active: Optional[bool] = None


class JobOut(JobBase):
    id: int

    class Config:
        from_attributes = True
