"""What a preset would change, and what it would leave alone.

The loader never changes anything. It reports the difference between the
preset and the tenant's own configuration, and the tenant decides.

The report has four parts, because there are four different things that
can happen:

``add``
    The preset proposes a value the tenant does not have.
``unchanged``
    The tenant already has that value.
``overwrite``
    The tenant has a different value. The report says what the preset
    would have put there, and the tenant's value wins: a preset is a
    suggestion the customer may refuse.
``undecided``
    The preset cannot decide. The slot holds the sentinel, and only a
    verified rule pack can fill it.

The tenant's own settings, and the tenant's own modules, are left alone
and are reported as such.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from app.core.presets.sentinel import is_sentinel
from app.core.presets.tenant_state import TenantState

#: The preset proposes a value the tenant does not have.
ACTION_ADD = "add"

#: The tenant already has that value.
ACTION_UNCHANGED = "unchanged"

#: The tenant has a different value, and it wins.
ACTION_OVERWRITE = "overwrite"

#: The preset cannot decide the value.
ACTION_UNDECIDED = "undecided"

#: The tenant has a value the preset says nothing about.
ACTION_TENANT_ONLY = "tenant_only"


@dataclass(frozen=True)
class SettingChange:
    """One setting, and what the preset would do with it."""

    path: str
    module: str
    action: str
    preset_value: Any = None
    tenant_value: Any = None
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "module": self.module,
            "action": self.action,
            "preset_value": self.preset_value,
            "tenant_value": self.tenant_value,
            "note": self.note,
        }


@dataclass(frozen=True)
class PresetDifference:
    """The difference between a preset and a tenant's configuration."""

    preset_id: str
    preset_version: str
    adds: tuple[SettingChange, ...] = ()
    unchanged: tuple[SettingChange, ...] = ()
    overwrites: tuple[SettingChange, ...] = ()
    undecided: tuple[SettingChange, ...] = ()
    tenant_only: tuple[SettingChange, ...] = ()
    modules_to_enable: tuple[str, ...] = ()
    modules_left_alone: tuple[str, ...] = ()
    exclusions: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "preset_id": self.preset_id,
            "preset_version": self.preset_version,
            "adds": [change.as_dict() for change in self.adds],
            "unchanged": [change.as_dict() for change in self.unchanged],
            "overwrites": [change.as_dict() for change in self.overwrites],
            "undecided": [change.as_dict() for change in self.undecided],
            "tenant_only": [change.as_dict() for change in self.tenant_only],
            "modules_to_enable": list(self.modules_to_enable),
            "modules_left_alone": list(self.modules_left_alone),
            "exclusions": [dict(item) for item in self.exclusions],
        }


def _leaves(block: dict, prefix: str) -> Iterator[tuple[str, Any]]:
    """Every setting inside a configuration block, with its path.

    A description is documentation, not a setting, so it is never a leaf.
    """
    for key, value in block.items():
        if key == "description":
            continue
        path = f"{prefix}.{key}"
        if isinstance(value, dict):
            yield from _leaves(value, path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                item_path = f"{path}[{index}]"
                if isinstance(item, dict):
                    yield from _leaves(item, item_path)
                else:
                    yield item_path, item
        else:
            yield path, value


def flatten_configuration(configuration: dict) -> list[tuple[str, str, Any]]:
    """Every setting a preset's configuration carries.

    Returns ``(module, path, value)`` for each one. The path is the
    module key and then the path inside the module's block, so
    ``leave.leave_types[0].entitlement_days`` is one setting.
    """
    rows: list[tuple[str, str, Any]] = []
    for module, block in sorted((configuration or {}).items()):
        if not isinstance(block, dict):
            continue
        for path, value in _leaves(block, module):
            rows.append((module, path, value))
    return rows


def diff_preset(preset, state: TenantState) -> PresetDifference:
    """Report what the preset would change, and what it would leave alone.

    The tenant's own configuration always wins. An overwrite is reported so
    that the customer can see the difference, and the tenant's value is
    the one that stands.
    """
    adds: list[SettingChange] = []
    unchanged: list[SettingChange] = []
    overwrites: list[SettingChange] = []
    undecided: list[SettingChange] = []
    preset_paths: set[str] = set()

    for module, path, preset_value in flatten_configuration(preset.configuration):
        preset_paths.add(path)
        if is_sentinel(preset_value):
            undecided.append(
                SettingChange(
                    path=path,
                    module=module,
                    action=ACTION_UNDECIDED,
                    preset_value=preset_value,
                    tenant_value=state.value(path) if state.has(path) else None,
                    note=(
                        "the preset does not decide this value; a verified rule "
                        "pack fills it"
                    ),
                )
            )
            continue
        if not state.has(path):
            adds.append(
                SettingChange(
                    path=path,
                    module=module,
                    action=ACTION_ADD,
                    preset_value=preset_value,
                    tenant_value=None,
                    note="the preset proposes this value; the tenant has none",
                )
            )
            continue
        tenant_value = state.value(path)
        if tenant_value == preset_value:
            unchanged.append(
                SettingChange(
                    path=path,
                    module=module,
                    action=ACTION_UNCHANGED,
                    preset_value=preset_value,
                    tenant_value=tenant_value,
                    note="the tenant already has this value",
                )
            )
        else:
            overwrites.append(
                SettingChange(
                    path=path,
                    module=module,
                    action=ACTION_OVERWRITE,
                    preset_value=preset_value,
                    tenant_value=tenant_value,
                    note=(
                        "the tenant's value wins; the preset's value is not "
                        "applied"
                    ),
                )
            )

    tenant_only: list[SettingChange] = []
    for path in state.paths():
        if path in preset_paths:
            continue
        tenant_only.append(
            SettingChange(
                path=path,
                module=path.split(".", 1)[0] if "." in path else path,
                action=ACTION_TENANT_ONLY,
                preset_value=None,
                tenant_value=state.value(path),
                note="the preset says nothing about this value; it is the tenant's",
            )
        )

    tenant_enabled = state.enabled_modules()
    preset_default = set(preset.enabled_by_default)
    modules_to_enable = tuple(sorted(preset_default - tenant_enabled))
    modules_left_alone = tuple(sorted(tenant_enabled - preset_default))

    return PresetDifference(
        preset_id=preset.preset_id,
        preset_version=preset.version,
        adds=tuple(adds),
        unchanged=tuple(unchanged),
        overwrites=tuple(overwrites),
        undecided=tuple(undecided),
        tenant_only=tuple(tenant_only),
        modules_to_enable=modules_to_enable,
        modules_left_alone=modules_left_alone,
        exclusions=tuple(dict(item) for item in preset.exclusions),
    )
