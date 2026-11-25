"""The modules the product actually serves.

A preset may only offer a module the product has. A preset that suggests a
module that is not built is a broken promise, made during setup, to somebody
who is deciding whether to trust the product.

This module is the inventory the loader checks a preset against, and it is
derived from the running application rather than from a list somebody
maintains: a module is available only when the routers that implement it
are registered in the API. Remove a router and the module stops being
offerable, and the test suite says so.

The ``requires`` edges here are the product's own. A preset may add an
edge; it may not remove one. The effective graph is the union of the two,
and the union is what the server enforces.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleSpec:
    """One module of the product.

    :param key: the module key, the one a preset names.
    :param title: the name the customer sees.
    :param routers: the API router tags that implement the module. The
        module is served when every one of them is registered.
    :param requires: the modules the product needs for this one to work.
    """

    key: str
    title: str
    routers: tuple[str, ...]
    requires: tuple[str, ...]
    description: str


#: Every module the product serves.
MODULES: dict[str, ModuleSpec] = {
    spec.key: spec
    for spec in (
        ModuleSpec(
            key="workforce",
            title="Workforce & Organisation",
            routers=("employees", "departments", "jobs", "core-hr"),
            requires=(),
            description=(
                "Employee records, the organisation chart, departments and jobs. "
                "Every other module needs people to work on."
            ),
        ),
        ModuleSpec(
            key="onboarding",
            title="Onboarding & Offboarding",
            routers=("onboarding", "offboarding"),
            requires=("workforce",),
            description=(
                "The checklists and documents that bring an employee in, and the "
                "ones that let them go."
            ),
        ),
        ModuleSpec(
            key="time_tracking",
            title="Time Tracking",
            routers=("time",),
            requires=("workforce",),
            description=(
                "Clocking in, timesheets and the recorded hours the payroll run "
                "is calculated from."
            ),
        ),
        ModuleSpec(
            key="time",
            title="Working Time & Breaks",
            routers=("time",),
            requires=("time_tracking",),
            description=(
                "The working-time model: the week, the grace period, the rounding "
                "and the break rules."
            ),
        ),
        ModuleSpec(
            key="scheduling",
            title="Scheduling",
            routers=("scheduling",),
            requires=("workforce",),
            description=(
                "Shift templates, the roster and the swaps between shifts."
            ),
        ),
        ModuleSpec(
            key="leave",
            title="Leave",
            routers=("leave",),
            requires=("workforce",),
            description=(
                "Leave types, balances, requests and the approvals that answer them."
            ),
        ),
        ModuleSpec(
            key="payroll",
            title="Payroll",
            routers=("payroll",),
            requires=("workforce",),
            description=(
                "The pay run and the payslips. It stays disabled until a verified "
                "rule pack is attached to the tenant."
            ),
        ),
        ModuleSpec(
            key="recruiting",
            title="Recruiting",
            routers=("requisitions", "candidates", "applications", "offers"),
            requires=("workforce",),
            description=(
                "Requisitions, candidates, applications and the offer that turns an "
                "application into a hire."
            ),
        ),
        ModuleSpec(
            key="reporting",
            title="Reporting",
            routers=("reports",),
            requires=("workforce",),
            description="The organisation-wide figures and the exports behind them.",
        ),
        ModuleSpec(
            key="forecasting",
            title="Forecasting",
            routers=("forecasting",),
            requires=("time_tracking",),
            description="Demand and headcount forecasts built from the recorded history.",
        ),
        ModuleSpec(
            key="ess",
            title="Employee Self-Service",
            routers=("ess-hr",),
            requires=("workforce",),
            description="The screens the workforce uses for themselves.",
        ),
        ModuleSpec(
            key="benefits",
            title="Benefits",
            routers=("benefits",),
            requires=("workforce",),
            description="The benefits the tenant offers and the enrolment in them.",
        ),
        ModuleSpec(
            key="learning",
            title="Learning",
            routers=("learning",),
            requires=("workforce",),
            description="Courses, enrolments and the record of what was completed.",
        ),
        ModuleSpec(
            key="performance",
            title="Performance",
            routers=("performance",),
            requires=("workforce",),
            description="Goals, reviews and the conversations that follow them.",
        ),
        ModuleSpec(
            key="compliance",
            title="Compliance",
            routers=("compliance",),
            requires=("workforce",),
            description=(
                "The compliance rules, the violations they find and the headcount "
                "plan."
            ),
        ),
        ModuleSpec(
            key="imports",
            title="Data Import",
            routers=("import-export",),
            requires=("workforce",),
            description=(
                "The templates and the dry run that bring the tenant's own records in."
            ),
        ),
        ModuleSpec(
            key="data_quality",
            title="Data Quality",
            routers=("data-quality",),
            requires=("workforce",),
            description="The checks that find the gaps and the duplicates in the data.",
        ),
    )
}


def served_router_tags() -> set[str]:
    """The API router tags the running application serves.

    The import is deferred: the API registry imports the endpoint modules,
    and the endpoint modules import this package, so importing it at module
    level would be a cycle.

    FastAPI >=0.118 keeps included routers lazy: the registry holds an
    ``_IncludedRouter`` placeholder instead of the endpoint routes. The
    ``tags=[...]`` passed to ``include_router`` live on the placeholder's
    ``include_context`` while the placeholder's own ``tags`` stay empty and
    the inner routes carry only the endpoint-module tags, so the walk takes
    the union of the placeholder tags, the include-context tags and the
    inner tags — the same way the security matrix enumerates served
    operations — so the inventory reflects the application that runs.
    On FastAPI <=0.111 the routers are expanded eagerly and the tags sit on
    each route, which the same walk still reads, so the detector works on
    both layouts.
    """
    from app.api.v1.api import api_router  # noqa: PLC0415 - deferred on purpose

    tags: set[str] = set()

    def _walk(routes) -> None:
        for route in routes:
            for tag in getattr(route, "tags", None) or ():
                tags.add(str(tag))
            context = getattr(route, "include_context", None)
            for tag in getattr(context, "tags", None) or ():
                tags.add(str(tag))
            original = getattr(route, "original_router", None)
            if original is not None and hasattr(original, "routes"):
                _walk(original.routes)

    _walk(api_router.routes)
    return tags


def available_modules() -> dict[str, ModuleSpec]:
    """The modules the running application actually serves.

    A module is available when every router that implements it is
    registered. A module whose router is not there is a module the product
    does not have, and no preset may offer it.
    """
    served = served_router_tags()
    return {
        key: spec
        for key, spec in MODULES.items()
        if all(router in served for router in spec.routers)
    }


def module_keys() -> list[str]:
    """The keys of the modules the product serves, in a stable order."""
    return sorted(available_modules())


def is_known_module(key: str) -> bool:
    """True when the product serves a module with this key."""
    return key in available_modules()
