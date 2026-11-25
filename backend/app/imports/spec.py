"""The CSV import contract.

One place that says what a CSV for each entity may contain: which columns
exist, which are required, what type each one is, which values are allowed,
which columns point at another entity, and which columns hold personal data
that must never be echoed back in an error.

Why a contract rather than a column list
----------------------------------------
The previous implementation kept the column list in the endpoint module and
the type rules in a set of module-level frozensets. Nothing checked the two
against each other, so a column could be accepted by the header resolver and
then silently written as a string. Every rule now lives in one :class:`EntitySpec`
per entity, and the header resolver, the validator, the template builder and
the documentation all read from it. Adding a column means adding it once.

The rules the contract encodes
------------------------------
*Exact headers.* A header is accepted if it matches a canonical column
exactly, case-insensitively, or if it is a documented alias. Anything else
is rejected and the full list of accepted headers is returned. There is no
fuzzy matching — a guess that resolves to the wrong column is worse than a
rejection the operator can act on.

*References by natural key.* A CSV names the thing it points at by the key a
human recognises (``job_code``), not by a database id that only exists after
another import has run. The importer resolves the key to an id and reports a
``reference_not_found`` error when it cannot.

*Masked personal data.* A column marked ``sensitive`` never has its value
included in an error message, in the row-error CSV, or in a log line. The
error names the column and the rule that was broken, and nothing else.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.benefits import BenefitPlan
from app.models.compliance import ComplianceRule
from app.models.core_hr import CostCenter, Location
from app.models.department import Department
from app.models.employee import Employee
from app.models.job import Job
from app.models.learning import Course
from app.models.leave import LeaveBalance, LeaveType
from app.models.payroll import PayComponent
from app.models.recruiting import Candidate
from app.models.scheduling import ShiftTemplate


@dataclass(frozen=True)
class ColumnSpec:
    """One column of one importable entity.

    ``name``
        The canonical column name. It is the name used in the template, in
        the documentation, and in the error messages.
    ``kind``
        How the value is parsed and validated. One of ``text``, ``code``,
        ``integer``, ``decimal``, ``boolean``, ``date``, ``datetime``,
        ``time``, ``email``.
    ``required``
        Whether the column must be present and non-blank. A required column
        may name ``alternatives``: at least one of the group must be present.
    ``target``
        The model attribute the value is written to. It differs from ``name``
        only for reference columns, where the CSV says ``job_code`` and the
        model says ``job_id``.
    ``reference``
        The entity a reference column points at, and ``reference_by`` says
        whether the value is that entity's natural key or its numeric id.
    ``sensitive``
        Whether the value is personal. Sensitive values are never echoed
        back.
    """

    name: str
    kind: str = "text"
    required: bool = False
    alternatives: tuple[str, ...] = ()
    enum: tuple[str, ...] = ()
    reference: str | None = None
    reference_by: str = "id"
    target: str | None = None
    sensitive: bool = False
    max_length: int | None = None
    minimum: float | None = None
    maximum: float | None = None
    description: str = ""

    @property
    def writes_to(self) -> str:
        """The model attribute this column is written to."""
        return self.target or self.name

    @property
    def required_group(self) -> tuple[str, ...]:
        """The names that satisfy this column's requirement."""
        return (self.name, *self.alternatives)


@dataclass(frozen=True)
class ConsistencyRule:
    """A rule that spans two columns of the same row.

    ``lower`` must not be greater than ``higher``. Both are compared as
    numbers, and a row that has only one of them is not checked.
    """

    lower: str
    higher: str
    message: str


@dataclass(frozen=True)
class EntitySpec:
    """Everything the importer needs to know about one entity."""

    name: str
    model: type
    columns: tuple[ColumnSpec, ...]
    natural_key: tuple[str, ...]
    label: str = ""
    consistency: tuple[ConsistencyRule, ...] = ()
    #: Whether the entity is written through a ledger rather than straight
    #: into its table. A ledger-backed entity's numbers are the projection
    #: of its history, so the importer writes the history and lets the
    #: ledger refresh the cache.
    writes_through_ledger: bool = False

    def column(self, name: str) -> ColumnSpec | None:
        for col in self.columns:
            if col.name == name:
                return col
        return None

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(col.name for col in self.columns)

    @property
    def required_groups(self) -> tuple[tuple[str, ...], ...]:
        """Requirement groups. Every group must be satisfied by every row."""
        return tuple(
            col.required_group for col in self.columns if col.required
        )

    @property
    def sensitive_columns(self) -> frozenset[str]:
        return frozenset(col.name for col in self.columns if col.sensitive)

    def reference_columns(self) -> tuple[ColumnSpec, ...]:
        return tuple(col for col in self.columns if col.reference)

    def natural_key_columns(self) -> tuple[ColumnSpec, ...]:
        return tuple(
            col for col in self.columns if col.name in self.natural_key
        )

    @property
    def natural_key_targets(self) -> tuple[str, ...]:
        """The model attributes the natural key is made of.

        For most entities this is the natural key itself. It differs for
        ``leave_balances``, whose CSV names an employee by their employee
        number and a leave type by its code, while the table stores the two
        ids.
        """
        return tuple(
            col.writes_to for col in self.columns if col.name in self.natural_key
        )

    @property
    def alternative_columns(self) -> frozenset[str]:
        """The columns that exist only as an alternative to another column.

        ``job_code`` is an alternative to ``job_id``: a file may use either,
        but the template shows only one of them, because a template that
        offers both tells the operator to fill in both.
        """
        names: set[str] = set()
        for column in self.columns:
            names.update(column.alternatives)
        return frozenset(names)

    @property
    def primary_columns(self) -> tuple[ColumnSpec, ...]:
        """The columns the template shows: one per alternative group."""
        alternatives = self.alternative_columns
        return tuple(
            column for column in self.columns if column.name not in alternatives
        )


# --------------------------------------------------------------------------
# Shared column fragments
# --------------------------------------------------------------------------

_ID = ColumnSpec(name="id", kind="integer", description=(
    "Database identifier. Ignored on import; identifiers are assigned by the "
    "database."
))

_ACTIVE = ColumnSpec(name="is_active", kind="boolean", description=(
    "Whether the record is in use. Defaults to true."
))


def _spec(
    name: str,
    model: type,
    columns,
    natural_key,
    label: str = "",
    consistency: tuple[ConsistencyRule, ...] = (),
    writes_through_ledger: bool = False,
) -> EntitySpec:
    return EntitySpec(
        name=name,
        model=model,
        columns=tuple(columns),
        natural_key=tuple(natural_key),
        label=label or name,
        consistency=consistency,
        writes_through_ledger=writes_through_ledger,
    )


# --------------------------------------------------------------------------
# The entities
# --------------------------------------------------------------------------

DEPARTMENTS = _spec(
    "departments",
    Department,
    [
        _ID,
        ColumnSpec("name", "text", required=True, max_length=200,
                   description="Display name of the department."),
        ColumnSpec("code", "code", required=True, max_length=20,
                   description="Short unique code, e.g. ENG. The natural key."),
        ColumnSpec("description", "text", max_length=2000,
                   description="Free-text description."),
        _ACTIVE,
    ],
    ("code",),
    "Departments",
)

JOBS = _spec(
    "jobs",
    Job,
    [
        _ID,
        ColumnSpec("title", "text", required=True, max_length=200,
                   description="Job title, e.g. 'Senior Engineer'."),
        ColumnSpec("code", "code", required=True, max_length=20,
                   description="Short unique code. The natural key."),
        ColumnSpec("department_id", "integer", required=True,
                   alternatives=("department_code",),
                   reference="departments", reference_by="id",
                   target="department_id",
                   description="Department id, or the department code."),
        ColumnSpec("department_code", "code",
                   reference="departments", reference_by="natural",
                   target="department_id",
                   description="Department code. Resolved to the department id."),
        ColumnSpec("min_salary", "decimal", sensitive=True, minimum=0,
                   description="Minimum salary for the band, per pay period."),
        ColumnSpec("max_salary", "decimal", sensitive=True, minimum=0,
                   description="Maximum salary for the band, per pay period."),
        _ACTIVE,
    ],
    ("code",),
    "Jobs",
    consistency=(
        ConsistencyRule(
            "min_salary",
            "max_salary",
            "'min_salary' must not be greater than 'max_salary'",
        ),
    ),
)
LOCATIONS = _spec(
    "locations",
    Location,
    [
        _ID,
        ColumnSpec("name", "text", required=True, max_length=160,
                   description="Display name of the site."),
        ColumnSpec("code", "code", required=True, max_length=20,
                   description="Short unique code. The natural key."),
        ColumnSpec("address", "text", max_length=2000,
                   description="Street address."),
        ColumnSpec("city", "text", max_length=100, description="City."),
        ColumnSpec("country", "text", max_length=80, description="Country."),
        ColumnSpec("timezone", "text", max_length=60,
                   description="IANA timezone, e.g. Europe/London."),
        _ACTIVE,
    ],
    ("code",),
    "Locations",
)

EMPLOYEES = _spec(
    "employees",
    Employee,
    [
        _ID,
        ColumnSpec("employee_id", "code", required=True, max_length=50,
                   description=(
                       "The employee number, e.g. EMP-0001. The natural key; "
                       "unique and permanent."
                   )),
        ColumnSpec("first_name", "text", required=True, max_length=100,
                   sensitive=True, description="Given name."),
        ColumnSpec("last_name", "text", required=True, max_length=100,
                   sensitive=True, description="Family name."),
        ColumnSpec("email", "email", required=True, max_length=255,
                   sensitive=True, description="Work email address."),
        ColumnSpec("phone", "text", max_length=30, sensitive=True,
                   description="Contact phone number."),
        ColumnSpec("hire_date", "date", required=True,
                   description="Start date, ISO 8601 (YYYY-MM-DD)."),
        ColumnSpec("job_id", "integer", required=True,
                   alternatives=("job_code",),
                   reference="jobs", reference_by="id", target="job_id",
                   description="Job id, or the job code."),
        ColumnSpec("job_code", "code", reference="jobs", reference_by="natural",
                   target="job_id",
                   description="Job code. Resolved to the job id."),
        ColumnSpec("department_id", "integer", required=True,
                   alternatives=("department_code",),
                   reference="departments", reference_by="id",
                   target="department_id",
                   description="Department id, or the department code."),
        ColumnSpec("department_code", "code", reference="departments",
                   reference_by="natural", target="department_id",
                   description="Department code. Resolved to the department id."),
        ColumnSpec("manager_id", "integer",
                   alternatives=("manager_employee_id",),
                   reference="employees", reference_by="id", target="manager_id",
                   description="Manager's employee id, or their employee number."),
        ColumnSpec("manager_employee_id", "code", reference="employees",
                   reference_by="natural", target="manager_id",
                   description="Manager's employee number."),
        ColumnSpec("status", "text", max_length=20,
                   enum=("Active", "On Leave", "Terminated", "Rehired"),
                   description="Employment status."),
        ColumnSpec("salary", "decimal", sensitive=True, minimum=0,
                   description=(
                       "Base salary, per pay period. See the salary unit "
                       "decision in the import documentation."
                   )),
    ],
    ("employee_id",),
    "Employees",
)

LEAVE_BALANCES = _spec(
    "leave_balances",
    LeaveBalance,
    [
        _ID,
        ColumnSpec("employee_number", "code", required=True,
                   alternatives=("employee_id",),
                   reference="employees", reference_by="natural",
                   target="employee_id",
                   description="Employee number. Resolved to the employee id."),
        ColumnSpec("employee_id", "integer", reference="employees",
                   reference_by="id", target="employee_id",
                   description="Employee id, if the number is not used."),
        ColumnSpec("leave_type_code", "code", required=True,
                   alternatives=("leave_type_id",),
                   reference="leave_types", reference_by="natural",
                   target="leave_type_id",
                   description="Leave type code, e.g. ANN. Resolved to the id."),
        ColumnSpec("leave_type_id", "integer", reference="leave_types",
                   reference_by="id", target="leave_type_id",
                   description="Leave type id, if the code is not used."),
        ColumnSpec("entitlement_year", "integer", required=True, minimum=1970,
                   maximum=2999, description="Calendar year the balance is for."),
        ColumnSpec("entitled_days", "decimal", minimum=0,
                   description="Days entitled for the year."),
        ColumnSpec("carried_over_days", "decimal", minimum=0,
                   description="Days carried over from the previous year."),
        ColumnSpec("used_days", "decimal", minimum=0,
                   description="Days already used."),
    ],
    ("employee_number", "leave_type_code", "entitlement_year"),
    "Leave balances",
    writes_through_ledger=True,
)

SHIFT_TEMPLATES = _spec(
    "shift_templates",
    ShiftTemplate,
    [
        _ID,
        ColumnSpec("name", "text", required=True, max_length=100,
                   description="Display name, e.g. 'Day 09:00-17:00'."),
        ColumnSpec("code", "code", required=True, max_length=20,
                   description="Short unique code. The natural key."),
        ColumnSpec("start_time", "time", required=True,
                   description="Start time, 24-hour HH:MM."),
        ColumnSpec("end_time", "time", required=True,
                   description="End time, 24-hour HH:MM."),
        ColumnSpec("break_minutes", "integer", minimum=0, maximum=1440,
                   description="Unpaid break length in minutes."),
        ColumnSpec("is_night", "boolean", description="Whether this is a night shift."),
        _ACTIVE,
    ],
    ("code",),
    "Shift templates",
)

# --- Additional entities, carried over from the previous implementation ----

COST_CENTERS = _spec(
    "cost_centers",
    CostCenter,
    [
        _ID,
        ColumnSpec("code", "code", required=True, max_length=20,
                   description="Short unique code. The natural key."),
        ColumnSpec("name", "text", required=True, max_length=160,
                   description="Display name."),
        ColumnSpec("department_id", "integer",
                   alternatives=("department_code",),
                   reference="departments", reference_by="id",
                   target="department_id", description="Department id or code."),
        ColumnSpec("department_code", "code", reference="departments",
                   reference_by="natural", target="department_id",
                   description="Department code."),
        _ACTIVE,
    ],
    ("code",),
    "Cost centres",
)

CANDIDATES = _spec(
    "candidates",
    Candidate,
    [
        _ID,
        ColumnSpec("first_name", "text", required=True, max_length=100,
                   sensitive=True, description="Given name."),
        ColumnSpec("last_name", "text", required=True, max_length=100,
                   sensitive=True, description="Family name."),
        ColumnSpec("email", "email", required=True, max_length=255,
                   sensitive=True, description="Email address."),
        ColumnSpec("phone", "text", max_length=30, sensitive=True,
                   description="Contact phone number."),
        ColumnSpec("source", "text", max_length=60,
                   description="Where the candidate came from."),
        ColumnSpec("status", "text", max_length=20,
                   enum=("Applied", "Screening", "Interview", "Offer", "Hired",
                         "Rejected", "Withdrawn"),
                   description="Pipeline status."),
    ],
    ("email",),
    "Candidates",
)

LEAVE_TYPES = _spec(
    "leave_types",
    LeaveType,
    [
        _ID,
        ColumnSpec("name", "text", required=True, max_length=80,
                   description="Display name, e.g. 'Annual Leave'."),
        ColumnSpec("code", "code", required=True, max_length=20,
                   description="Short unique code. The natural key."),
        ColumnSpec("is_paid", "boolean", description="Whether the leave is paid."),
        ColumnSpec("max_days_per_year", "decimal", minimum=0,
                   description="Maximum days per year."),
        _ACTIVE,
    ],
    ("code",),
    "Leave types",
)

BENEFIT_PLANS = _spec(
    "benefit_plans",
    BenefitPlan,
    [
        _ID,
        ColumnSpec("name", "text", required=True, max_length=120,
                   description="Display name."),
        ColumnSpec("code", "code", required=True, max_length=20,
                   description="Short unique code. The natural key."),
        ColumnSpec("plan_type", "text", max_length=40,
                   enum=("Health", "Pension", "Life", "Dental", "Other"),
                   description="Kind of benefit."),
        ColumnSpec("provider", "text", max_length=120,
                   description="Insurer or provider."),
        ColumnSpec("employer_contribution", "decimal", sensitive=True, minimum=0,
                   description="Employer's monthly contribution."),
        ColumnSpec("employee_contribution", "decimal", sensitive=True, minimum=0,
                   description="Employee's monthly contribution."),
        _ACTIVE,
    ],
    ("code",),
    "Benefit plans",
)

COURSES = _spec(
    "courses",
    Course,
    [
        _ID,
        ColumnSpec("title", "text", required=True, max_length=200,
                   description="Course title."),
        ColumnSpec("code", "code", required=True, max_length=20,
                   description="Short unique code. The natural key."),
        ColumnSpec("description", "text", max_length=2000,
                   description="Free-text description."),
        ColumnSpec("category", "text", max_length=60,
                   description="Course category."),
        ColumnSpec("duration_hours", "decimal", minimum=0,
                   description="Length in hours."),
        ColumnSpec("is_mandatory", "boolean",
                   description="Whether the course is mandatory."),
        _ACTIVE,
    ],
    ("code",),
    "Courses",
)

COMPLIANCE_RULES = _spec(
    "compliance_rules",
    ComplianceRule,
    [
        _ID,
        ColumnSpec("code", "code", required=True, max_length=40,
                   description="Short unique code. The natural key."),
        ColumnSpec("name", "text", required=True, max_length=160,
                   description="Display name."),
        ColumnSpec("category", "text", max_length=60,
                   description="Rule category."),
        ColumnSpec("description", "text", max_length=2000,
                   description="Free-text description."),
        ColumnSpec("severity", "text", max_length=20,
                   enum=("Low", "Medium", "High", "Critical"),
                   description="How serious a breach is."),
        _ACTIVE,
    ],
    ("code",),
    "Compliance rules",
)

PAY_COMPONENTS = _spec(
    "pay_components",
    PayComponent,
    [
        _ID,
        ColumnSpec("code", "code", required=True, max_length=20,
                   description="Short unique code. The natural key."),
        ColumnSpec("name", "text", required=True, max_length=120,
                   description="Display name."),
        ColumnSpec("component_type", "text", required=True, max_length=20,
                   enum=("Earning", "Deduction", "Tax"),
                   description="Whether it adds to or subtracts from pay."),
        ColumnSpec("is_taxable", "boolean", description="Whether it is taxable."),
        ColumnSpec("is_pre_tax", "boolean", description="Whether it is pre-tax."),
        _ACTIVE,
    ],
    ("code",),
    "Pay components",
)


#: Every importable entity, keyed by name.
ENTITIES: dict[str, EntitySpec] = {
    spec.name: spec
    for spec in (
        DEPARTMENTS,
        JOBS,
        LOCATIONS,
        EMPLOYEES,
        LEAVE_BALANCES,
        SHIFT_TEMPLATES,
        COST_CENTERS,
        CANDIDATES,
        LEAVE_TYPES,
        BENEFIT_PLANS,
        COURSES,
        COMPLIANCE_RULES,
        PAY_COMPONENTS,
    )
}

#: The entities the import documentation and the golden files cover.
CORE_ENTITIES = (
    "departments",
    "locations",
    "jobs",
    "employees",
    "leave_balances",
    "shift_templates",
)


def get_spec(entity: str) -> EntitySpec | None:
    return ENTITIES.get(entity)


def entity_models() -> dict[str, type]:
    """Entity name -> model, for reference resolution."""
    return {name: spec.model for name, spec in ENTITIES.items()}
