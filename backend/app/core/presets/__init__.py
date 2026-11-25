"""The preset engine.

A preset is a versioned, reusable starting configuration that a customer
selects during onboarding. It is a document, not a decision: the customer
may accept it, change it or refuse it, and the tenant's own configuration
always wins over the preset's.

The package holds:

* :mod:`app.core.presets.loader` — reads a preset and holds it to the
  contract and to the rules the contract leaves to the server;
* :mod:`app.core.presets.modules` — the modules the product actually
  serves, which is what a preset may offer;
* :mod:`app.core.presets.graph` — the module dependency graph and the
  refusal of a configuration that breaks it;
* :mod:`app.core.presets.diff` — what a preset would change, and what it
  would leave alone;
* :mod:`app.core.presets.provenance` — whether a value came from the
  preset, from the customer, or from the customer's change to it;
* :mod:`app.core.presets.readiness` — what is configured, what is missing,
  what is inconsistent and what is merely recommended;
* :mod:`app.core.presets.statutory` and :mod:`app.core.presets.sentinel` —
  the rule that a preset carries no statutory value.
"""
from app.core.presets.diff import PresetDifference, SettingChange, diff_preset, flatten_configuration
from app.core.presets.graph import ModuleGraph, check_module_enablement
from app.core.presets.loader import (
    Preset,
    load_all_presets,
    load_preset,
    preset_ids,
    preset_problems,
)
from app.core.presets.modules import available_modules, module_keys
from app.core.presets.provenance import ProvenanceRecord, provenance_report
from app.core.presets.readiness import ReadinessFinding, ReadinessReport, TenantFacts, check_readiness
from app.core.presets.sentinel import SENTINEL, contains_sentinel, is_sentinel
from app.core.presets.statutory import statutory_violations
from app.core.presets.tenant_state import TenantState, read_state, write_state

__all__ = [
    "ModuleGraph",
    "Preset",
    "PresetDifference",
    "ProvenanceRecord",
    "ReadinessFinding",
    "ReadinessReport",
    "SENTINEL",
    "SettingChange",
    "TenantFacts",
    "TenantState",
    "available_modules",
    "check_module_enablement",
    "check_readiness",
    "contains_sentinel",
    "diff_preset",
    "flatten_configuration",
    "is_sentinel",
    "load_all_presets",
    "load_preset",
    "module_keys",
    "preset_ids",
    "preset_problems",
    "provenance_report",
    "read_state",
    "statutory_violations",
    "write_state",
]
