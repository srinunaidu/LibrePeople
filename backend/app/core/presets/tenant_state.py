"""The tenant's own configuration, as the presets see it.

One deployment serves one customer, so the configuration the presets are
compared against is deployment level. It lives in one row of
``tenant_preset_state``:

* the preset the deployment uses, and the version of it;
* the modules the deployment switched on;
* the settings the deployment configured, each with where the value came
  from.

The provenance of a setting is what makes the difference between a preset
and a configuration. A value that still equals the preset's proposal came
from the preset. A value that differs from it was changed by the customer.
A value the preset never proposed is the customer's own. The customer can
see which is which, and the product never guesses.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.onboarding import TenantPresetState

#: The scope of the deployment's own preset state.
DEPLOYMENT_SCOPE = "deployment"

#: The provenance of a value that still is the preset's proposal.
SOURCE_PRESET_DEFAULT = "preset_default"

#: The provenance of a value the customer changed.
SOURCE_TENANT_OVERRIDE = "tenant_override"

#: The provenance of a value the customer set where the preset said nothing.
SOURCE_TENANT_SET = "tenant_set"

#: The provenance sources a customer may record.
RECORDED_SOURCES = (SOURCE_PRESET_DEFAULT, SOURCE_TENANT_OVERRIDE, SOURCE_TENANT_SET)


@dataclass(frozen=True)
class TenantState:
    """What the tenant has configured."""

    preset_id: str | None = None
    preset_version: str | None = None
    modules: dict[str, bool] = field(default_factory=dict)
    settings: dict[str, dict[str, Any]] = field(default_factory=dict)
    preset_document: dict[str, Any] | None = None
    corrupt: bool = False

    def has(self, path: str) -> bool:
        """True when the tenant has a value at this path."""
        return path in self.settings

    def value(self, path: str) -> Any:
        """The tenant's value at this path, or ``None``."""
        entry = self.settings.get(path)
        if not isinstance(entry, dict):
            return None
        return entry.get("value")

    def source(self, path: str) -> str | None:
        """The provenance the tenant recorded for this path, if any."""
        entry = self.settings.get(path)
        if not isinstance(entry, dict):
            return None
        source = entry.get("source")
        return str(source) if source in RECORDED_SOURCES else None

    def enabled_modules(self) -> set[str]:
        """The modules the tenant switched on."""
        return {key for key, value in self.modules.items() if value}

    def paths(self) -> list[str]:
        """Every path the tenant has a value at."""
        return sorted(self.settings)


def _loads(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return fallback


def read_state(db: Session) -> TenantState:
    """Read the deployment's preset state.

    A deployment that has never chosen a preset has an empty state, and
    the readiness check says everything is missing rather than failing.
    """
    row = (
        db.query(TenantPresetState)
        .filter(TenantPresetState.scope == DEPLOYMENT_SCOPE)
        .first()
    )
    if row is None:
        return TenantState()

    corrupt = False
    modules = _loads(row.modules_json, None)
    settings = _loads(row.settings_json, None)
    document = _loads(row.preset_document, None)
    if not isinstance(modules, dict):
        modules, corrupt = {}, True
    if not isinstance(settings, dict):
        settings, corrupt = {}, True
    if document is not None and not isinstance(document, dict):
        document, corrupt = None, True

    return TenantState(
        preset_id=row.preset_id,
        preset_version=row.preset_version,
        modules={str(key): bool(value) for key, value in modules.items()},
        settings={
            str(key): value if isinstance(value, dict) else {"value": value}
            for key, value in settings.items()
        },
        preset_document=document,
        corrupt=corrupt,
    )


def write_state(
    db: Session,
    *,
    preset_id: str | None = None,
    preset_version: str | None = None,
    modules: dict[str, bool] | None = None,
    settings: dict[str, dict[str, Any]] | None = None,
    preset_document: dict[str, Any] | None = None,
) -> TenantState:
    """Record the deployment's preset state.

    The row is created the first time it is written and updated after
    that, so the state of a deployment that has never chosen a preset is
    an empty state rather than a missing row.
    """
    row = (
        db.query(TenantPresetState)
        .filter(TenantPresetState.scope == DEPLOYMENT_SCOPE)
        .first()
    )
    if row is None:
        row = TenantPresetState(scope=DEPLOYMENT_SCOPE)
        db.add(row)

    row.preset_id = preset_id
    row.preset_version = preset_version
    row.modules_json = json.dumps(modules or {}, sort_keys=True)
    row.settings_json = json.dumps(settings or {}, sort_keys=True)
    row.preset_document = (
        json.dumps(preset_document, sort_keys=True) if preset_document is not None else None
    )
    db.add(row)
    db.flush()
    return read_state(db)
