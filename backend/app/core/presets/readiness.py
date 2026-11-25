"""The readiness check.

What is configured, what is missing, what is inconsistent and what is
merely recommended. Every finding names the gap and says what to do about
it. The check changes nothing: it reads the tenant's configuration, the
tenant's own data and the preset, and it reports.

Four categories, because a customer acts on them differently:

``configured``
    It is in place.
``missing``
    It is not there yet.
``inconsistent``
    It is there, and it contradicts something else.
``recommended``
    It is not there, and the preset suggests it.

The rules are two sets. The product's own rules are always run: a module
whose dependency is off, a setting that is still waiting for a rule pack,
data that has not been imported. The preset's own validations are run as
well, so a preset says what it needs and the check says so in the
customer's words.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.core.presets.graph import ModuleGraph
from app.core.presets.modules import available_modules
from app.core.presets.sentinel import contains_sentinel, is_sentinel
from app.core.presets.tenant_state import TenantState

#: The finding is in place.
CONFIGURED = "configured"

#: The finding is not in place.
MISSING = "missing"

#: The finding contradicts something else.
INCONSISTENT = "inconsistent"

#: The finding is a suggestion from the preset.
RECOMMENDED = "recommended"

#: The finding stops the setup from being called ready.
BLOCKING = "blocking"

#: The finding should be looked at.
WARNING = "warning"

#: The finding is information.
INFO = "info"


@dataclass(frozen=True)
class ReadinessFinding:
    """One thing the readiness check found."""

    rule_id: str
    category: str
    severity: str
    message: str
    fix_target: str
    entity: str | None = None
    module: str | None = None
    auto_fixable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "fix_target": self.fix_target,
            "entity": self.entity,
            "module": self.module,
            "auto_fixable": self.auto_fixable,
        }


@dataclass(frozen=True)
class ReadinessReport:
    """What the readiness check found."""

    preset_id: str | None = None
    preset_version: str | None = None
    configured: tuple[ReadinessFinding, ...] = ()
    missing: tuple[ReadinessFinding, ...] = ()
    inconsistent: tuple[ReadinessFinding, ...] = ()
    recommended: tuple[ReadinessFinding, ...] = ()
    findings: tuple[ReadinessFinding, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "preset_version": self.preset_version,
            "configured": [finding.as_dict() for finding in self.configured],
            "missing": [finding.as_dict() for finding in self.missing],
            "inconsistent": [finding.as_dict() for finding in self.inconsistent],
            "recommended": [finding.as_dict() for finding in self.recommended],
            "findings": [finding.as_dict() for finding in self.findings],
        }

    @property
    def blocking(self) -> tuple[ReadinessFinding, ...]:
        """The findings that stop the setup from being called ready."""
        return tuple(finding for finding in self.findings if finding.severity == BLOCKING)


@dataclass(frozen=True)
class TenantFacts:
    """What the tenant's own data already holds."""

    employees: int = 0
    departments: int = 0
    jobs: int = 0
    leave_types: int = 0
    shift_templates: int = 0
    department_codes: tuple[str, ...] = ()
    job_codes: tuple[str, ...] = ()
    leave_type_codes: tuple[str, ...] = ()
    shift_template_codes: tuple[str, ...] = ()

    def count(self, entity: str) -> int:
        """How many records of an entity the tenant has."""
        return {
            "employees": self.employees,
            "departments": self.departments,
            "jobs": self.jobs,
            "leave_types": self.leave_types,
            "shift_templates": self.shift_templates,
            "locations": 0,
        }.get(entity, 0)

    def codes(self, entity: str) -> tuple[str, ...]:
        """The keys the tenant already has for an entity."""
        return {
            "departments": self.department_codes,
            "jobs": self.job_codes,
            "leave_types": self.leave_type_codes,
            "shift_templates": self.shift_template_codes,
        }.get(entity, ())


def read_facts(db: Session) -> TenantFacts:
    """Read what the tenant's own data holds.

    The check reads other lanes' tables; it never writes to them.
    """
    from app.models.department import Department
    from app.models.employee import Employee
    from app.models.job import Job
    from app.models.leave import LeaveType
    from app.models.scheduling import ShiftTemplate

    departments = db.query(Department).all()
    jobs = db.query(Job).all()
    leave_types = db.query(LeaveType).all()
    shift_templates = db.query(ShiftTemplate).all()

    return TenantFacts(
        employees=db.query(Employee).count(),
        departments=len(departments),
        jobs=len(jobs),
        leave_types=len(leave_types),
        shift_templates=len(shift_templates),
        department_codes=tuple(str(row.code) for row in departments),
        job_codes=tuple(str(row.code) for row in jobs),
        leave_type_codes=tuple(str(row.code) for row in leave_types),
        shift_template_codes=tuple(str(row.code) for row in shift_templates),
    )


def _condition_holds(
    condition: dict,
    state: TenantState,
    preset,
    facts: TenantFacts,
    graph: ModuleGraph,
) -> bool:
    """Evaluate one condition of a preset's validation."""
    kind = str(condition.get("kind", ""))
    if kind == "module_enabled":
        return str(condition.get("module", "")) in state.enabled_modules()
    if kind == "module_dependency_met":
        module = str(condition.get("module", ""))
        return not any(problem.module == module for problem in graph.unmet(state.enabled_modules()))
    if kind == "setting_present":
        return state.has(str(condition.get("path", "")))
    if kind == "no_unresolved_sentinels":
        module = condition.get("module")
        for path in state.paths():
            if module and not path.startswith(f"{module}."):
                continue
            if contains_sentinel(state.value(path)):
                return False
        return True
    if kind == "data_present":
        return facts.count(str(condition.get("entity", ""))) > 0
    return False


#: The category a failed condition of each kind belongs to.
_CONDITION_CATEGORY = {
    "module_enabled": MISSING,
    "module_dependency_met": INCONSISTENT,
    "setting_present": MISSING,
    "no_unresolved_sentinels": INCONSISTENT,
    "data_present": MISSING,
}


def check_readiness(
    state: TenantState,
    preset,
    facts: TenantFacts,
) -> ReadinessReport:
    """Report what is configured, missing, inconsistent and recommended.

    The check reads. It never writes, never enables a module and never
    changes a setting.
    """
    configured: list[ReadinessFinding] = []
    missing: list[ReadinessFinding] = []
    inconsistent: list[ReadinessFinding] = []
    recommended: list[ReadinessFinding] = []

    graph = ModuleGraph.for_preset(preset) if preset is not None else ModuleGraph.product_graph()
    enabled = state.enabled_modules()

    # --- the preset itself ------------------------------------------------
    if state.preset_id:
        configured.append(
            ReadinessFinding(
                rule_id="setup.preset_selected",
                category=CONFIGURED,
                severity=INFO,
                message=(
                    f"The deployment uses the preset {state.preset_id}"
                    + (f" version {state.preset_version}." if state.preset_version else ".")
                ),
                fix_target="onboarding.preset",
                entity="preset",
            )
        )
    else:
        missing.append(
            ReadinessFinding(
                rule_id="setup.preset_selected",
                category=MISSING,
                severity=BLOCKING,
                message=(
                    "No preset has been selected for this deployment. A preset is "
                    "a suggestion: choosing one is how the setup starts."
                ),
                fix_target="onboarding.preset",
                entity="preset",
            )
        )

    if state.corrupt:
        inconsistent.append(
            ReadinessFinding(
                rule_id="setup.state_readable",
                category=INCONSISTENT,
                severity=BLOCKING,
                message=(
                    "The stored preset state of this deployment cannot be read. "
                    "It has to be repaired before the setup can be judged."
                ),
                fix_target="onboarding.preset",
            )
        )

    # --- the modules ------------------------------------------------------
    if enabled:
        configured.append(
            ReadinessFinding(
                rule_id="setup.modules_enabled",
                category=CONFIGURED,
                severity=INFO,
                message=(
                    f"{len(enabled)} modules are enabled: " + ", ".join(sorted(enabled)) + "."
                ),
                fix_target="onboarding.modules",
                entity="module",
            )
        )
    else:
        missing.append(
            ReadinessFinding(
                rule_id="setup.modules_enabled",
                category=MISSING,
                severity=BLOCKING,
                message="No module is enabled, so the product has nothing to show.",
                fix_target="onboarding.modules",
                entity="module",
            )
        )

    unmet = graph.unmet(enabled)
    for problem in unmet:
        inconsistent.append(
            ReadinessFinding(
                rule_id="modules.dependency_met",
                category=INCONSISTENT,
                severity=BLOCKING,
                message=problem.detail.capitalize() + ".",
                fix_target="onboarding.modules",
                entity="module",
                module=problem.module,
            )
        )
    if enabled and not unmet:
        configured.append(
            ReadinessFinding(
                rule_id="modules.dependency_met",
                category=CONFIGURED,
                severity=INFO,
                message="Every enabled module has the modules it requires.",
                fix_target="onboarding.modules",
                entity="module",
            )
        )

    served = set(available_modules())
    for module in sorted(enabled - served):
        inconsistent.append(
            ReadinessFinding(
                rule_id="modules.known",
                category=INCONSISTENT,
                severity=BLOCKING,
                message=(
                    f"The module {module} is enabled but the application does not "
                    "serve it."
                ),
                fix_target="onboarding.modules",
                entity="module",
                module=module,
            )
        )
    if enabled and enabled <= served:
        configured.append(
            ReadinessFinding(
                rule_id="modules.known",
                category=CONFIGURED,
                severity=INFO,
                message="Every enabled module is served by the application.",
                fix_target="onboarding.modules",
                entity="module",
            )
        )

    # --- the settings -----------------------------------------------------
    waiting = [
        path
        for path in state.paths()
        if contains_sentinel(state.value(path))
    ]
    for path in waiting:
        inconsistent.append(
            ReadinessFinding(
                rule_id="settings.rule_pack_resolved",
                category=INCONSISTENT,
                severity=BLOCKING,
                message=(
                    f"The setting {path} is still waiting for a verified rule "
                    "pack. It cannot be used until one is attached."
                ),
                fix_target=path,
                module=path.split(".", 1)[0] if "." in path else None,
            )
        )
    if state.paths() and not waiting:
        configured.append(
            ReadinessFinding(
                rule_id="settings.rule_pack_resolved",
                category=CONFIGURED,
                severity=INFO,
                message="Every configured setting has a value; none is waiting for a rule pack.",
                fix_target="onboarding.settings",
                entity="setting",
            )
        )

    # --- the tenant's own data -------------------------------------------
    data_rules = (
        ("data.employees", "employees", "employees", "import-export", "employee"),
        ("data.departments", "departments", "workforce", "departments", "department"),
        ("data.jobs", "jobs", "workforce", "jobs", "job"),
        ("data.leave_types", "leave_types", "leave", "leave.leave_types", "leave type"),
        ("data.shift_templates", "shift_templates", "scheduling", "scheduling.shift_templates", "shift template"),
    )
    for rule_id, entity, module, fix_target, label in data_rules:
        if module not in enabled:
            continue
        count = facts.count(entity)
        if count:
            configured.append(
                ReadinessFinding(
                    rule_id=rule_id,
                    category=CONFIGURED,
                    severity=INFO,
                    message=f"The tenant has {count} {label}(s).",
                    fix_target=fix_target,
                    entity=entity,
                    module=module,
                )
            )
        else:
            missing.append(
                ReadinessFinding(
                    rule_id=rule_id,
                    category=MISSING,
                    severity=WARNING if entity != "shift_templates" else INFO,
                    message=f"The tenant has no {label} yet.",
                    fix_target=fix_target,
                    entity=entity,
                    module=module,
                )
            )

    # --- the preset's own validations -------------------------------------
    if preset is not None:
        for validation in preset.validations:
            condition = validation.get("condition") or {}
            kind = str(condition.get("kind", ""))
            if _condition_holds(condition, state, preset, facts, graph):
                configured.append(
                    ReadinessFinding(
                        rule_id=str(validation.get("key", rule_id_default())),
                        category=CONFIGURED,
                        severity=INFO,
                        message=f"{validation.get('name', 'The check')} passes.",
                        fix_target=str(validation.get("fix_target", "onboarding")),
                        module=validation.get("module"),
                    )
                )
                continue
            inconsistent.append(
                ReadinessFinding(
                    rule_id=str(validation.get("key", "preset.validation")),
                    category=_CONDITION_CATEGORY.get(kind, MISSING),
                    severity=str(validation.get("severity", WARNING)),
                    message=str(validation.get("message", "A setup check did not pass.")),
                    fix_target=str(validation.get("fix_target", "onboarding")),
                    module=validation.get("module"),
                )
            )

        # --- what the preset recommends -----------------------------------
        recommended.extend(_recommendations(preset, facts, enabled))

    findings = tuple(configured + missing + inconsistent + recommended)
    return ReadinessReport(
        preset_id=state.preset_id,
        preset_version=state.preset_version,
        configured=tuple(configured),
        missing=tuple(missing),
        inconsistent=tuple(inconsistent),
        recommended=tuple(recommended),
        findings=findings,
    )


def rule_id_default() -> str:
    """The rule id used when a validation does not name one."""
    return "preset.validation"


def _recommendations(preset, facts: TenantFacts, enabled: set[str]) -> list[ReadinessFinding]:
    """What the preset suggests and the tenant does not have yet."""
    found: list[ReadinessFinding] = []

    organisation = preset.document.get("organisation_templates") or {}
    for department in organisation.get("departments") or []:
        key = str(department.get("key", ""))
        if key and key not in facts.department_codes:
            found.append(
                ReadinessFinding(
                    rule_id="preset.department_recommended",
                    category=RECOMMENDED,
                    severity=INFO,
                    message=(
                        f"The preset suggests the department {department.get('name')}; "
                        "the tenant has not created it."
                    ),
                    fix_target=f"departments.{key}",
                    entity="department",
                    module="workforce",
                )
            )

    leave_types = (preset.configuration.get("leave") or {}).get("leave_types") or []
    for leave_type in leave_types:
        key = str(leave_type.get("key", ""))
        if key and key not in facts.leave_type_codes:
            found.append(
                ReadinessFinding(
                    rule_id="preset.leave_type_recommended",
                    category=RECOMMENDED,
                    severity=INFO,
                    message=(
                        f"The preset suggests the leave type {leave_type.get('name')}; "
                        "the tenant has not created it."
                    ),
                    fix_target=f"leave.leave_types.{key}",
                    entity="leave_type",
                    module="leave",
                )
            )

    shift_templates = (preset.configuration.get("scheduling") or {}).get("shift_templates") or []
    for template in shift_templates:
        key = str(template.get("key", ""))
        if key and key not in facts.shift_template_codes:
            found.append(
                ReadinessFinding(
                    rule_id="preset.shift_template_recommended",
                    category=RECOMMENDED,
                    severity=INFO,
                    message=(
                        f"The preset suggests the shift template {template.get('name')}; "
                        "the tenant has not created it."
                    ),
                    fix_target=f"scheduling.shift_templates.{key}",
                    entity="shift_template",
                    module="scheduling",
                )
            )

    if facts.employees == 0:
        for template in preset.document.get("import_templates") or []:
            if str(template.get("entity")) != "employees":
                continue
            found.append(
                ReadinessFinding(
                    rule_id="preset.import_template_recommended",
                    category=RECOMMENDED,
                    severity=INFO,
                    message=(
                        "The tenant has no employees yet. The preset points at the "
                        f"{template.get('name')} template for them."
                    ),
                    fix_target=str(template.get("endpoint", "import-export")),
                    entity="employees",
                    module="imports",
                )
            )

    return found
