"""Header resolution and formula-injection neutralisation.

Header resolution
-----------------
A header is resolved to a canonical column name in three steps:

1. an exact match against the canonical name;
2. a case-insensitive match against the canonical name;
3. a match against the documented alias table.

Anything else is unknown. Unknown headers are a rejection, not a warning, and
the rejection carries the full list of headers the entity accepts so the
operator can fix the file without reading the documentation.

There is deliberately no fuzzy matching. A header that *almost* matches is
more dangerous than one that does not match at all: a guess that resolves to
the wrong column writes the wrong value into the wrong place, and nothing
downstream notices.

Formula injection
-----------------
OWASP's guidance on CSV injection is that a cell whose first character is
``=``, ``+``, ``-``, ``@``, tab or carriage return is executed as a formula
by a spreadsheet application when the file is opened. The neutraliser
prefixes such a cell with a single quote, which makes it literal text.

One carve-out, and it is a deliberate one: a cell that parses as a number is
a number, not a formula. ``-1000`` in a salary column is a negative number;
turning it into ``'-1000`` would corrupt the data and then fail to parse.
The carve-out only applies to the two characters that double as a sign
(``-`` and ``+``), and only when the remainder of the cell parses cleanly as
a number. Everything else in the trigger set is neutralised unconditionally.
"""
from __future__ import annotations

import re

#: Canonical column name -> the alternative spellings that resolve to it.
#:
#: The alias table is documentation as much as code: every alias here appears
#: in ``docs/IMPORT_TEMPLATES.md`` and in the error the operator sees when
#: they use one, so the set of accepted spellings is never a secret.
HEADER_ALIASES: dict[str, frozenset[str]] = {
    "id": frozenset({"id", "identifier", "uid"}),
    "name": frozenset({"name", "full_name", "department_name", "location_name"}),
    "code": frozenset({
        "code", "department_code", "job_code", "location_code",
        "leave_type_code", "benefit_plan_code", "course_code",
        "compliance_rule_code", "shift_template_code", "pay_component_code",
        "cost_center_code",
    }),
    "title": frozenset({"title", "job_title", "position_title", "course_title"}),
    "description": frozenset({"description", "desc", "details"}),
    "is_active": frozenset({"is_active", "active"}),
    "employee_id": frozenset({
        "employee_id", "employee_code", "emp_id", "staff_id",
        "personnel_number",
    }),
    "employee_number": frozenset({
        "employee_number", "employee_no", "employee_code", "emp_id",
        "staff_id", "personnel_number",
    }),
    "first_name": frozenset({"first_name", "firstname", "given_name"}),
    "last_name": frozenset({"last_name", "lastname", "surname", "family_name"}),
    "email": frozenset({"email", "email_address", "work_email"}),
    "phone": frozenset({"phone", "phone_number", "telephone", "mobile"}),
    "hire_date": frozenset({"hire_date", "date_of_hire"}),
    "job_id": frozenset({"job_id", "job_code"}),
    "job_code": frozenset({"job_code", "job_code_id", "position_code"}),
    "department_id": frozenset({"department_id", "department_code", "dept_code"}),
    "department_code": frozenset({"department_code", "dept_code"}),
    "manager_id": frozenset({"manager_id", "manager_code", "reports_to"}),
    "manager_employee_id": frozenset({
        "manager_employee_id", "manager_employee_number", "manager_code",
    }),
    "status": frozenset({"status", "employment_status"}),
    "salary": frozenset({"salary", "base_salary"}),
    "min_salary": frozenset({"min_salary", "minimum_salary"}),
    "max_salary": frozenset({"max_salary", "maximum_salary"}),
    "leave_type_id": frozenset({"leave_type_id", "leave_type_code"}),
    "leave_type_code": frozenset({"leave_type_code", "leave_type"}),
    "max_days_per_year": frozenset({
        "max_days_per_year", "annual_allowance", "entitlement_days",
    }),
    "is_paid": frozenset({"is_paid", "paid"}),
    "plan_type": frozenset({"plan_type", "type"}),
    "provider": frozenset({"provider", "insurer"}),
    "employer_contribution": frozenset({
        "employer_contribution", "employer_contrib",
    }),
    "employee_contribution": frozenset({
        "employee_contribution", "employee_contrib",
    }),
    "course_id": frozenset({"course_id", "course_code"}),
    "category": frozenset({"category", "cat"}),
    "duration_hours": frozenset({"duration_hours", "duration", "hours"}),
    "is_mandatory": frozenset({"is_mandatory", "mandatory"}),
    "plan_id": frozenset({"plan_id", "benefit_plan_code"}),
    "rule_id": frozenset({"rule_id", "compliance_rule_code"}),
    "position_id": frozenset({"position_id", "position_code"}),
    "break_minutes": frozenset({"break_minutes", "break_duration", "break_length"}),
    "fte": frozenset({"fte", "full_time_equivalent"}),
    "start_time": frozenset({"start_time", "shift_start"}),
    "end_time": frozenset({"end_time", "shift_end"}),
    "is_night": frozenset({"is_night", "night_shift"}),
    "entitlement_year": frozenset({"entitlement_year", "year"}),
    "entitled_days": frozenset({"entitled_days", "entitlement", "days_entitled"}),
    "carried_over_days": frozenset({
        "carried_over_days", "carry_over_days", "carried_over",
    }),
    "used_days": frozenset({"used_days", "days_used"}),
    "address": frozenset({"address", "street_address"}),
    "city": frozenset({"city", "town"}),
    "country": frozenset({"country", "country_code"}),
    "timezone": frozenset({"timezone", "time_zone", "tz"}),
    "source": frozenset({"source", "recruitment_source"}),
    "severity": frozenset({"severity", "risk_level"}),
    "component_type": frozenset({"component_type", "pay_component_type"}),
    "is_taxable": frozenset({"is_taxable", "taxable"}),
    "is_pre_tax": frozenset({"is_pre_tax", "pre_tax"}),
}

#: The characters OWASP names as formula-injection triggers.
FORMULA_TRIGGERS = frozenset({"=", "+", "-", "@", "\t", "\r"})

#: The two trigger characters that are also the sign of a number.
_NUMERIC_SIGNS = frozenset({"+", "-"})

_NUMBER_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")


def _looks_numeric(value: str) -> bool:
    return bool(_NUMBER_RE.match(value.strip()))


def resolve_header(raw_header: str | None, canonical_names) -> str | None:
    """Resolve one raw header to a canonical column name, or ``None``."""
    if raw_header is None:
        return None
    raw = raw_header.strip()
    if not raw:
        return None
    if raw in canonical_names:
        return raw
    lowered = raw.lower()
    for name in canonical_names:
        if name.lower() == lowered:
            return name
    for canonical, aliases in HEADER_ALIASES.items():
        if canonical not in canonical_names:
            continue
        if lowered in {alias.lower() for alias in aliases}:
            return canonical
    return None


def resolve_headers(raw_headers, canonical_names):
    """Resolve every raw header.

    Returns ``(resolved, unknown)`` where ``resolved`` maps the raw header
    to its canonical name and ``unknown`` lists the headers that could not
    be resolved.

    A canonical name that appears twice in the file is reported as unknown:
    two columns with the same name is ambiguous, and picking one of them
    would silently drop the other.
    """
    resolved: dict[str, str] = {}
    unknown: list[str] = []
    seen: set[str] = set()
    for header in raw_headers:
        canonical = resolve_header(header, canonical_names)
        if canonical is None:
            unknown.append(header)
            continue
        if canonical in seen:
            unknown.append(header)
            continue
        seen.add(canonical)
        resolved[header] = canonical
    return resolved, unknown


def neutralise_formula_injection(value: str) -> str:
    """Make a cell literal text rather than a formula.

    A cell whose first character is one of ``=``, ``+``, ``-``, ``@``, tab or
    carriage return is prefixed with a single quote.

    The exception is a cell that is a number: ``-1000`` is a negative number,
    not a formula, and prefixing it would corrupt it. The exception applies
    only to ``+`` and ``-``, and only when the whole cell parses as a
    number.
    """
    if not value:
        return value
    first = value[0]
    if first not in FORMULA_TRIGGERS:
        return value
    if first in _NUMERIC_SIGNS and _looks_numeric(value):
        return value
    return "'" + value
