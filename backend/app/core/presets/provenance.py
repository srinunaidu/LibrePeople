"""Where a configured value came from.

Every setting a tenant holds has a provenance, and the provenance is one of
four things:

``preset_default``
    The tenant's value is the preset's proposal, unchanged. The value came
    from the preset.
``tenant_override``
    The tenant's value differs from the preset's proposal. The tenant
    changed it.
``tenant_set``
    The tenant has a value where the preset proposed nothing.
``unresolved_rule_pack``
    The preset proposed the sentinel, so the value can only come from a
    verified rule pack.

A customer who overrode a preset is a customer whose configuration is
theirs. The product says so, per value, rather than leaving the customer
to guess which of their settings the preset still owns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.presets.sentinel import is_sentinel
from app.core.presets.tenant_state import (
    SOURCE_PRESET_DEFAULT,
    SOURCE_TENANT_OVERRIDE,
    SOURCE_TENANT_SET,
    TenantState,
)

#: The value came from the preset and was not changed.
PRESET_DEFAULT = SOURCE_PRESET_DEFAULT

#: The tenant changed the value the preset proposed.
TENANT_OVERRIDE = SOURCE_TENANT_OVERRIDE

#: The tenant set a value the preset did not propose.
TENANT_SET = SOURCE_TENANT_SET

#: The tenant has not set the value.
NOT_SET = "not_set"

#: The value can only come from a verified rule pack.
UNRESOLVED_RULE_PACK = "unresolved_rule_pack"

#: Every provenance a value may have.
PROVENANCE_STATES = (
    PRESET_DEFAULT,
    TENANT_OVERRIDE,
    TENANT_SET,
    NOT_SET,
    UNRESOLVED_RULE_PACK,
)


@dataclass(frozen=True)
class ProvenanceRecord:
    """The provenance of one setting."""

    path: str
    module: str
    state: str
    origin: str
    preset_value: Any = None
    tenant_value: Any = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "module": self.module,
            "state": self.state,
            "origin": self.origin,
            "preset_value": self.preset_value,
            "tenant_value": self.tenant_value,
        }


def module_of(path: str) -> str:
    """The module a setting path belongs to."""
    return path.split(".", 1)[0] if "." in path else path


def classify(
    preset_value: Any,
    tenant_value: Any,
    *,
    tenant_has_value: bool,
) -> str:
    """The provenance of one value.

    ``tenant_has_value`` says whether the tenant holds a value at all,
    because ``None`` is a value a tenant may hold.
    """
    if not tenant_has_value:
        if is_sentinel(preset_value):
            return UNRESOLVED_RULE_PACK
        return NOT_SET
    if is_sentinel(preset_value):
        return TENANT_SET
    if tenant_value == preset_value:
        return PRESET_DEFAULT
    return TENANT_OVERRIDE


def provenance_report(preset, state: TenantState) -> list[ProvenanceRecord]:
    """The provenance of every setting the preset and the tenant share.

    A provenance the tenant recorded wins over one the server derives: the
    customer knows where a value came from, and the server only compares.
    """
    from app.core.presets.diff import flatten_configuration

    records: list[ProvenanceRecord] = []
    seen: set[str] = set()

    for module, path, preset_value in flatten_configuration(preset.configuration):
        seen.add(path)
        recorded = state.source(path)
        if recorded is not None:
            records.append(
                ProvenanceRecord(
                    path=path,
                    module=module,
                    state=recorded,
                    origin="recorded",
                    preset_value=preset_value,
                    tenant_value=state.value(path),
                )
            )
            continue
        records.append(
            ProvenanceRecord(
                path=path,
                module=module,
                state=classify(
                    preset_value,
                    state.value(path),
                    tenant_has_value=state.has(path),
                ),
                origin="derived",
                preset_value=preset_value,
                tenant_value=state.value(path),
            )
        )

    for path in state.paths():
        if path in seen:
            continue
        records.append(
            ProvenanceRecord(
                path=path,
                module=module_of(path),
                state=TENANT_SET,
                origin="derived",
                preset_value=None,
                tenant_value=state.value(path),
            )
        )

    records.sort(key=lambda record: record.path)
    return records
