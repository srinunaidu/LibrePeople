"""The preset loader.

A preset is a versioned, schema-validated configuration package. This
module reads one, checks it against the contract in
``contracts/rules/preset.schema.json``, applies the rules the contract
leaves to the server, and hands back an object the rest of the product can
work with.

The server's own rules are the ones a schema cannot state:

* a preset must define every element the onboarding journey needs, so that
  a preset cannot be half-written;
* a preset may only name a module the product serves;
* a preset's dependency edges must resolve and must not form a cycle, and
  the modules it enables by default must be enabled legally;
* a preset may not carry a value a statute may set;
* the references a preset makes inside itself — the KPIs on a dashboard,
  the department a role sits in, the module a KPI reads from — must
  resolve.

About the bundled schema
------------------------
``preset.schema.json`` sits next to this module as well as in
``contracts/rules/``. The copy in ``contracts/`` is the contract; the copy
here is what the running application reads, because the backend image is
built from ``backend/`` and does not carry the ``contracts`` tree. The test
suite asserts that the two files are identical, so the copy cannot drift
away from the contract without the build going red.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

from app.core.errors import ApiError, ErrorCategory, validation
from app.core.presets.graph import ModuleGraph
from app.core.presets.modules import available_modules
from app.core.presets.statutory import statutory_violations

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
SCHEMA_PATH = PACKAGE_DIR / "preset.schema.json"
CONTRACT_SCHEMA_PATH = (
    Path(__file__).resolve().parents[4] / "contracts" / "rules" / "preset.schema.json"
)

#: The elements every preset must define. The onboarding journey reads
#: each of them, and a preset that leaves one out breaks a step of it.
#:
#: Each entry is the label a person reads and the path inside the document.
REQUIRED_ELEMENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("modules", ("modules",)),
    ("module configuration", ("configuration",)),
    ("organisation templates", ("organisation_templates",)),
    ("departments", ("organisation_templates", "departments")),
    ("job families", ("organisation_templates", "job_families")),
    ("roles", ("organisation_templates", "roles")),
    ("shift templates", ("configuration", "scheduling", "shift_templates")),
    ("leave types", ("configuration", "leave", "leave_types")),
    ("dashboards", ("dashboards", "dashboards")),
    ("key performance indicators", ("dashboards", "kpis")),
    ("action queues", ("dashboards", "action_queues")),
    ("forecast drivers", ("forecast_drivers", "drivers")),
    ("forecast data requirements", ("forecast_drivers", "required_data")),
    ("import templates", ("import_templates",)),
    ("setup validations", ("validations",)),
    ("exclusions", ("exclusions",)),
)

#: The condition kinds the readiness check knows how to evaluate. A
#: validation the server cannot evaluate is a validation that never fires.
KNOWN_CONDITION_KINDS: tuple[str, ...] = (
    "module_enabled",
    "module_dependency_met",
    "setting_present",
    "no_unresolved_sentinels",
    "data_present",
)

#: The arguments each condition kind must be given.
CONDITION_REQUIRED_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "module_enabled": ("module",),
    "module_dependency_met": ("module",),
    "setting_present": ("path",),
    "no_unresolved_sentinels": (),
    "data_present": ("entity",),
}

#: The arguments each condition kind may be given. An optional argument
#: narrows the check; without it the check covers everything.
CONDITION_OPTIONAL_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "module_enabled": (),
    "module_dependency_met": (),
    "setting_present": (),
    "no_unresolved_sentinels": ("module",),
    "data_present": (),
}

_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


@dataclass(frozen=True)
class Preset:
    """One preset: the document, and where it came from."""

    document: dict
    source: str
    origin: str

    # -- the header of the document ----------------------------------------

    @property
    def preset_id(self) -> str:
        return str(self.document.get("preset_id", ""))

    @property
    def name(self) -> str:
        return str(self.document.get("name", ""))

    @property
    def business_type(self) -> str:
        return str(self.document.get("business_type", ""))

    @property
    def version(self) -> str:
        return str(self.document.get("version", ""))

    @property
    def status(self) -> str:
        return str(self.document.get("status", ""))

    @property
    def description(self) -> str:
        return str(self.document.get("description", ""))

    @property
    def module_entries(self) -> list[dict]:
        entries = self.document.get("modules") or []
        return [entry for entry in entries if isinstance(entry, dict)]

    @property
    def module_keys(self) -> list[str]:
        return [str(entry.get("key", "")) for entry in self.module_entries]

    @property
    def configuration(self) -> dict:
        configuration = self.document.get("configuration") or {}
        return configuration if isinstance(configuration, dict) else {}

    @property
    def exclusions(self) -> list[dict]:
        exclusions = self.document.get("exclusions") or []
        return [item for item in exclusions if isinstance(item, dict)]

    @property
    def validations(self) -> list[dict]:
        validations = self.document.get("validations") or []
        return [item for item in validations if isinstance(item, dict)]

    @property
    def enabled_by_default(self) -> list[str]:
        return [
            str(entry.get("key", ""))
            for entry in self.module_entries
            if entry.get("enabled_by_default")
        ]

    def graph(self) -> ModuleGraph:
        """The effective dependency graph of this preset."""
        return ModuleGraph.for_preset(self)


# --- the schema -------------------------------------------------------------


@lru_cache(maxsize=1)
def preset_schema() -> dict:
    """The preset schema, read from the copy that ships with the package."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = preset_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def schema_errors(document: dict) -> list[str]:
    """Every way the document breaks the preset schema, in words."""
    problems: list[str] = []
    for error in sorted(_validator().iter_errors(document), key=lambda e: list(e.path)):
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        problems.append(f"{location}: {error.message}")
    return problems


# --- the server's own rules -------------------------------------------------


def _at(document: dict, path: Iterable[str]) -> Any:
    current: Any = document
    for segment in path:
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return current


def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict, str)):
        return len(value) > 0
    return True


def element_problems(document: dict) -> list[str]:
    """The elements the onboarding journey needs that the preset leaves out."""
    problems: list[str] = []
    for label, path in REQUIRED_ELEMENTS:
        if not _is_filled(_at(document, path)):
            problems.append(f"the preset does not define {label} ({'.'.join(path)})")
    return problems


def reference_problems(document: dict) -> list[str]:
    """The references a preset makes inside itself that do not resolve."""
    problems: list[str] = []
    modules = set(MODULE_KEYS_OF(document))
    known_modules = set(available_modules())

    organisation = document.get("organisation_templates") or {}
    departments = {
        str(item.get("key")) for item in organisation.get("departments") or [] if isinstance(item, dict)
    }
    families = {
        str(item.get("key")) for item in organisation.get("job_families") or [] if isinstance(item, dict)
    }
    for department in organisation.get("departments") or []:
        parent = department.get("parent_key")
        if parent and str(parent) not in departments:
            problems.append(
                f"the department {department.get('key')} names the parent {parent}, "
                "which the preset does not define"
            )
    for role in organisation.get("roles") or []:
        family = str(role.get("job_family_key", ""))
        department = str(role.get("department_key", ""))
        if family not in families:
            problems.append(
                f"the role {role.get('key')} names the job family {family}, "
                "which the preset does not define"
            )
        if department not in departments:
            problems.append(
                f"the role {role.get('key')} names the department {department}, "
                "which the preset does not define"
            )

    dashboards = document.get("dashboards") or {}
    kpis = {str(item.get("key")) for item in dashboards.get("kpis") or [] if isinstance(item, dict)}
    for dashboard in dashboards.get("dashboards") or []:
        for key in dashboard.get("kpi_keys") or []:
            if str(key) not in kpis:
                problems.append(
                    f"the dashboard {dashboard.get('key')} shows the indicator {key}, "
                    "which the preset does not define"
                )
    for indicator in dashboards.get("kpis") or []:
        source = str(indicator.get("source_module", ""))
        if source not in modules:
            problems.append(
                f"the indicator {indicator.get('key')} reads from the module {source}, "
                "which the preset does not define"
            )
        if source and source not in known_modules:
            problems.append(
                f"the indicator {indicator.get('key')} reads from the module {source}, "
                "which the application does not serve"
            )
    for queue in dashboards.get("action_queues") or []:
        source = str(queue.get("source_module", ""))
        if source not in modules:
            problems.append(
                f"the action queue {queue.get('key')} is filled by the module {source}, "
                "which the preset does not define"
            )

    forecast = document.get("forecast_drivers") or {}
    for driver in forecast.get("drivers") or []:
        source = str(driver.get("source_module", ""))
        if source not in modules:
            problems.append(
                f"the forecast driver {driver.get('key')} reads from the module {source}, "
                "which the preset does not define"
            )
    for requirement in forecast.get("required_data") or []:
        source = str(requirement.get("source_module", ""))
        if source not in modules:
            problems.append(
                f"the forecast data requirement {requirement.get('key')} is held by the "
                f"module {source}, which the preset does not define"
            )

    for validation in document.get("validations") or []:
        condition = validation.get("condition") or {}
        kind = str(condition.get("kind", ""))
        if kind not in KNOWN_CONDITION_KINDS:
            problems.append(
                f"the validation {validation.get('key')} uses the condition {kind}, "
                "which the server does not evaluate"
            )
            continue
        allowed = CONDITION_REQUIRED_ARGUMENTS[kind] + CONDITION_OPTIONAL_ARGUMENTS[kind]
        for argument in condition:
            if argument == "kind":
                continue
            if argument not in allowed:
                problems.append(
                    f"the validation {validation.get('key')} passes {argument} to the "
                    f"condition {kind}, which does not take it"
                )
        for argument in CONDITION_REQUIRED_ARGUMENTS[kind]:
            if argument not in condition:
                problems.append(
                    f"the validation {validation.get('key')} does not say which {argument} "
                    f"the condition {kind} is about"
                )
        module = str(condition.get("module", ""))
        if module and module not in modules:
            problems.append(
                f"the validation {validation.get('key')} is about the module {module}, "
                "which the preset does not define"
            )

    return problems


def MODULE_KEYS_OF(document: dict) -> list[str]:
    """The module keys a document declares."""
    entries = document.get("modules") or []
    return [str(entry.get("key", "")) for entry in entries if isinstance(entry, dict)]


def graph_problems(document: dict) -> list[str]:
    """The ways the preset's dependency graph is broken."""
    graph = ModuleGraph.for_preset(_as_preset(document))
    return [problem.detail for problem in graph.problems()]


def default_enablement_problems(document: dict) -> list[str]:
    """The ways the preset's own defaults break its dependency graph."""
    preset = _as_preset(document)
    graph = ModuleGraph.for_preset(preset)
    problems = []
    for problem in graph.unmet(preset.enabled_by_default):
        problems.append(
            f"the preset enables {problem.module} by default but "
            + ", ".join(problem.missing)
            + (" is" if len(problem.missing) == 1 else " are")
            + " not enabled by default"
        )
    return problems


def _as_preset(document: dict) -> Preset:
    return Preset(document=document, source="document", origin="document")


def preset_problems(document: dict) -> list[str]:
    """Every way the document breaks a rule the schema cannot state."""
    problems: list[str] = []
    problems.extend(schema_errors(document))
    if problems:
        # A document that does not match the shape cannot be checked
        # against the rules that assume the shape.
        return problems
    problems.extend(element_problems(document))
    problems.extend(reference_problems(document))
    problems.extend(graph_problems(document))
    problems.extend(default_enablement_problems(document))
    problems.extend(statutory_violations(document))
    version = str(document.get("version", ""))
    if not _SEMVER.match(version):
        problems.append(f"the version {version} is not a semantic version")
    return problems


# --- reading ----------------------------------------------------------------


def preset_not_found(preset_id: str) -> ApiError:
    """The refusal for a preset that does not exist.

    The code is the one the shared error contract publishes for it.
    """
    return ApiError(
        "preset_not_found",
        f"Preset {preset_id} not found",
        ErrorCategory.NOT_FOUND,
        details={"preset": preset_id},
    )


def preset_document_from_disk(preset_id: str) -> dict:
    """The document of a preset that ships with the product."""
    path = DATA_DIR / f"{preset_id}.json"
    if not path.exists():
        raise preset_not_found(preset_id)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise validation(
            "validation_error",
            f"the preset {preset_id} is not readable JSON",
            preset=preset_id,
            reason=str(exc),
        ) from exc


def load_preset(preset_id: str, *, document: dict | None = None) -> Preset:
    """Load one preset and check it.

    ``document`` is the document to load. When it is not given the preset
    is read from the disk, from the package's own data directory. A
    document held in the tenant's own configuration is loaded the same way,
    and is held to the same rules: a preset the tenant wrote is still a
    preset, and it may not carry a statutory number either.

    Raises :class:`app.core.errors.ApiError` with the code
    ``preset_not_found`` when there is no such preset, and with the code
    ``validation_error`` when the preset breaks a rule.
    """
    if document is None:
        document = preset_document_from_disk(preset_id)
        source, origin = "disk", str(DATA_DIR / f"{preset_id}.json")
    else:
        source, origin = "database", "tenant configuration"

    problems = preset_problems(document)
    if problems:
        raise validation(
            "validation_error",
            f"the preset {preset_id} is not valid: " + "; ".join(problems[:5]),
            preset=preset_id,
            problems=problems,
        )
    return Preset(document=document, source=source, origin=origin)


def load_all_presets() -> list[Preset]:
    """Every preset that ships with the product, in a stable order."""
    presets: list[Preset] = []
    for path in sorted(DATA_DIR.glob("*.json")):
        presets.append(load_preset(path.stem))
    return presets


def preset_ids() -> list[str]:
    """The identifiers of the presets that ship with the product."""
    return sorted(path.stem for path in DATA_DIR.glob("*.json"))


def preset_exists(preset_id: str) -> bool:
    """True when a preset with this identifier ships with the product."""
    return (DATA_DIR / f"{preset_id}.json").exists()
