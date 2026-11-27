"""The preset engine: the six presets, the dependency graph and the readiness check.

What this suite holds the product to:

* every preset loads, validates against the contract, and defines every
  element the onboarding journey reads;
* **no preset carries a statutory value** — every slot a statute may set
  holds the sentinel, and the loader refuses a preset that does not;
* **no preset offers a module the product does not serve** — the check is
  against the running application, not against a list;
* the module dependency graph is refused in code, every way it can be
  broken, with the missing dependency named;
* the loader reports what it would change and changes nothing;
* the readiness check reports and changes nothing, which is asserted
  against the database;
* the provenance tells a value the preset suggested from a value the
  customer set and from a value the customer overrode.

Run:  python onboarding_test_suite.py
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
from datetime import date
from pathlib import Path

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="onboarding_test_"), "onboarding_test.db")

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
# Field encryption (item 6: no SECRET_KEY fallback) — onboarding writes
# employee identity fields through app.core.encryption.
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.presets import (  # noqa: E402
    SENTINEL,
    check_module_enablement,
    diff_preset,
    load_all_presets,
    load_preset,
    preset_ids,
    preset_problems,
    provenance_report,
    statutory_violations,
)
from app.core.presets.graph import ModuleGraph  # noqa: E402
from app.core.presets.loader import (  # noqa: E402
    DATA_DIR,
    element_problems,
    preset_schema,
    reference_problems,
    schema_errors,
)
from app.core.presets.modules import available_modules, served_router_tags  # noqa: E402
from app.core.presets.readiness import check_readiness, read_facts  # noqa: E402
from app.core.presets.tenant_state import TenantState, read_state, write_state  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.leave import LeaveType  # noqa: E402
from app.models.onboarding import TenantPresetState  # noqa: E402
from app.models.scheduling import ShiftTemplate  # noqa: E402
from app.models.user import User  # noqa: E402
from app.main import app  # noqa: E402

Base.metadata.create_all(bind=engine)

session = SessionLocal()
session.add(User(
    username="preset_admin", email="preset_admin@example.com",
    hashed_password=get_password_hash("PresetPass12345"),
    role="SuperAdmin", is_active=True,
    mfa_enabled=True,  # MFA-enforced world: privileged users are enrolled
))
session.add(User(
    username="preset_associate", email="preset_associate@example.com",
    hashed_password=get_password_hash("PresetPass12345"),
    role="Associate", is_active=True,
))
session.add(Department(name="Store", code="STORE"))
session.flush()
session.add(Job(title="Shop Assistant", code="SHOP", department_id=1))
session.add(LeaveType(name="Annual Leave", code="annual-leave", is_paid=True))
session.add(ShiftTemplate(name="Early", code="early", start_time="06:00", end_time="14:00"))
session.add(Employee(
    employee_id="EMP-PRESET-1", first_name="Sam", last_name="Rivera",
    email="sam.preset@example.com", hire_date=date(2026, 1, 5),
    department_id=1, job_id=1,
))
session.commit()
session.close()

client = TestClient(app, raise_server_exceptions=False)

RESULTS = {"pass": 0, "fail": 0}
FAILURES: list[tuple[str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def token(username: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "PresetPass12345"},
    )
    return response.json()["access_token"]


ADMIN = {"Authorization": f"Bearer {token('preset_admin')}"}
ASSOCIATE = {"Authorization": f"Bearer {token('preset_associate')}"}

THE_SIX = [
    "retail",
    "construction",
    "hospitality",
    "healthcare_clinic",
    "light_manufacturing",
    "generic_office",
]


def document_of(preset_id: str) -> dict:
    return json.loads((DATA_DIR / f"{preset_id}.json").read_text(encoding="utf-8"))


def db_counts() -> dict[str, int]:
    """How many rows every table holds, so that a write cannot hide."""
    from sqlalchemy import inspect

    counts: dict[str, int] = {}
    inspector = inspect(engine)
    for table in inspector.get_table_names():
        with engine.connect() as connection:
            counts[table] = connection.exec_driver_sql(f"SELECT COUNT(*) FROM {table}").scalar()
    return counts


# ==========================================================================
print("=" * 68)
print("PRESETS — every one of the six loads and validates")
print("=" * 68)

check("the six decided presets ship with the product",
      sorted(preset_ids()) == sorted(THE_SIX), str(sorted(preset_ids())))

loaded = {}
for preset_id in THE_SIX:
    try:
        preset = load_preset(preset_id)
    except Exception as exc:  # noqa: BLE001 - per-preset isolation: one broken preset must not hide the other five
        check(f"{preset_id} loads", False, str(exc)[:300])
        continue
    loaded[preset_id] = preset
    check(f"{preset_id} loads", preset.preset_id == preset_id, preset.preset_id)

check("every one of the six presets loads",
      sorted(loaded) == sorted(THE_SIX),
      f"loaded={sorted(loaded)}")

check("the loader reports the version it loaded",
      all(preset.version == "1.0.0" for preset in loaded.values())
      and sorted(loaded) == sorted(THE_SIX),
      str({p: (loaded[p].version if p in loaded else "<did not load>") for p in THE_SIX}))

check("every preset validates against the contract",
      all(not schema_errors(document_of(p)) for p in THE_SIX),
      "; ".join(f"{p}: {schema_errors(document_of(p))[:2]}" for p in THE_SIX
                if schema_errors(document_of(p))))

check("every preset is published",
      sorted(loaded) == sorted(THE_SIX)
      and all(loaded[p].status == "published" for p in loaded),
      str({p: (loaded[p].status if p in loaded else "<did not load>") for p in THE_SIX}))

check("the bundled schema copy is the contract, byte for byte",
      (Path(__file__).resolve().parent / "app" / "core" / "presets" / "preset.schema.json").read_bytes()
      == (Path(__file__).resolve().parents[1] / "contracts" / "rules" / "preset.schema.json").read_bytes(),
      "the copy in the package and the contract in contracts/ differ")

# ==========================================================================
print()
print("=" * 68)
print("PRESETS — every one defines every element the journey reads")
print("=" * 68)

for preset_id in THE_SIX:
    document = document_of(preset_id)
    check(f"{preset_id} defines every element",
          not element_problems(document),
          "; ".join(element_problems(document)))

    check(f"{preset_id} resolves its own references",
          not reference_problems(document),
          "; ".join(reference_problems(document)[:3]))

    organisation = document["organisation_templates"]
    check(f"{preset_id} suggests departments, job families and roles",
          bool(organisation["departments"]) and bool(organisation["job_families"])
          and bool(organisation["roles"]),
          str(organisation.keys()))

    check(f"{preset_id} suggests shift templates and working patterns",
          bool(document["configuration"]["scheduling"]["shift_templates"]),
          "no shift templates")

    leave_types = document["configuration"]["leave"]["leave_types"]
    check(f"{preset_id} suggests leave types with accrual parameters",
          bool(leave_types) and all("accrual" in item for item in leave_types),
          str(len(leave_types)))

    check(f"{preset_id} suggests dashboards, indicators and action queues",
          bool(document["dashboards"]["dashboards"])
          and bool(document["dashboards"]["kpis"])
          and bool(document["dashboards"]["action_queues"]),
          str(document["dashboards"].keys()))

    check(f"{preset_id} names the forecast drivers and the data they need",
          bool(document["forecast_drivers"]["drivers"])
          and bool(document["forecast_drivers"]["required_data"]),
          str(document["forecast_drivers"].keys()))

    check(f"{preset_id} names the import templates that apply",
          bool(document["import_templates"]),
          "no import templates")

    check(f"{preset_id} says what it does not decide",
          bool(document["exclusions"])
          and all(item.get("reason") for item in document["exclusions"]),
          str(len(document.get("exclusions", []))))

    check(f"{preset_id} names the checks the setup runs",
          bool(document["validations"]),
          "no validations")

# ==========================================================================
print()
print("=" * 68)
print("PRESETS — no preset carries a statutory value")
print("=" * 68)

for preset_id in THE_SIX:
    document = document_of(preset_id)
    check(f"{preset_id} carries no statutory value",
          not statutory_violations(document),
          "; ".join(statutory_violations(document)[:3]))

# The sentinel is where the law's number would be.
retail = document_of("retail")
sentinel_slots = [
    retail["configuration"]["leave"]["leave_types"][0]["entitlement_days"],
    retail["configuration"]["leave"]["leave_types"][0]["carry_over_limit_days"],
    retail["configuration"]["leave"]["leave_types"][0]["encashment_allowed"],
    retail["configuration"]["leave"]["leave_types"][0]["expiry_rule"],
    retail["configuration"]["payroll"]["statutory_components"][0]["rate"],
    retail["configuration"]["payroll"]["statutory_leave_pay"]["leave_pay_rate"],
    retail["configuration"]["recruiting"]["background_check_consent_scope"],
    retail["configuration"]["time"]["break_rules"][0]["duration_minutes"],
    retail["configuration"]["time"]["break_rules"][0]["jurisdiction_specific"],
    retail["configuration"]["scheduling"]["shift_templates"][0]["break_length_minutes"],
    retail["configuration"]["scheduling"]["shift_templates"][0]["minimum_rest_hours"],
    retail["configuration"]["scheduling"]["shift_templates"][0]["max_consecutive_days"],
]
check("every statutory slot of the retail preset carries the sentinel",
      all(slot == SENTINEL for slot in sentinel_slots),
      str([slot for slot in sentinel_slots if slot != SENTINEL]))

# A preset that carries a number where the sentinel belongs is refused.
offending = copy.deepcopy(retail)
offending["configuration"]["leave"]["leave_types"][0]["entitlement_days"] = 25
check("a preset that states a leave entitlement is refused",
      bool(statutory_violations(offending)),
      "the loader accepted a statutory entitlement")
check("the refusal names the slot",
      any("entitlement_days" in problem for problem in statutory_violations(offending)),
      str(statutory_violations(offending)))

offending = copy.deepcopy(retail)
offending["configuration"]["payroll"]["statutory_components"][0]["rate"] = 12.5
check("a preset that states a tax rate is refused",
      bool(statutory_violations(offending)),
      "the loader accepted a statutory rate")

offending = copy.deepcopy(retail)
offending["configuration"]["scheduling"]["shift_templates"][0]["break_length_minutes"] = 30
check("a preset that states a break length is refused",
      bool(statutory_violations(offending)),
      "the loader accepted a break length")

offending = copy.deepcopy(retail)
offending["configuration"]["recruiting"]["background_check_consent_scope"] = "criminal-record"
check("a preset that asserts a consent scope is refused",
      bool(statutory_violations(offending)),
      "the loader accepted a consent scope")

# The loader refuses a preset that carries a statutory value.
try:
    load_preset("retail", document=offending)
    refused = False
    detail = "the loader accepted it"
except Exception as exc:  # noqa: BLE001 - the refusal is an ApiError
    refused = True
    detail = str(exc)
check("the loader refuses a preset that carries a statutory value", refused, detail)

# ==========================================================================
print()
print("=" * 68)
print("PRESETS — no preset offers a module the product does not have")
print("=" * 68)

served = available_modules()
check("the application serves the modules the presets name",
      all(key in served for key in
          {entry["key"] for preset_id in THE_SIX
           for entry in document_of(preset_id)["modules"]}),
      str(sorted(served)))

for preset_id in THE_SIX:
    document = document_of(preset_id)
    unknown = [entry["key"] for entry in document["modules"] if entry["key"] not in served]
    check(f"{preset_id} names only modules the application serves",
          not unknown, str(unknown))

# A preset that names a module the product does not have is refused.
offending = copy.deepcopy(retail)
offending["modules"].append({
    "key": "quantum_forecasting",
    "enabled_by_default": False,
    "requires": [],
    "description": "A module the product does not have.",
})
check("a preset that names a module the product does not have is refused",
      bool(preset_problems(offending)),
      str(preset_problems(offending)[:2]))

# A preset that is missing an element is refused.
offending = copy.deepcopy(retail)
del offending["organisation_templates"]
check("a preset that is missing an element is refused",
      bool(element_problems(offending)) and bool(preset_problems(offending)),
      str(element_problems(offending)[:2]))

# A preset that resolves a reference to nothing is refused.
offending = copy.deepcopy(retail)
offending["dashboards"]["dashboards"][0]["kpi_keys"].append("a-kpi-that-does-not-exist")
check("a preset that resolves a reference to nothing is refused",
      bool(reference_problems(offending)) and bool(preset_problems(offending)),
      str(reference_problems(offending)[:2]))

# A rate under a name the contract does not know is still refused.
offending = copy.deepcopy(retail)
offending["configuration"]["workforce"]["settings"]["minimum_hourly_rate"] = 12.5
check("a preset that states a rate under a name the contract does not know is refused",
      bool(statutory_violations(offending)) and bool(preset_problems(offending)),
      str(statutory_violations(offending)[:2]))

# ==========================================================================
print()
print("=" * 68)
print("THE DEPENDENCY GRAPH — refused in code, every way it can be broken")
print("=" * 68)

# 1. A module enabled while the module it requires is not.
try:
    check_module_enablement({"leave"})
    refused = False
    detail = "the configuration was accepted"
except Exception as exc:  # noqa: BLE001 - the refusal is an ApiError
    refused = True
    detail = f"{getattr(exc, 'code', '')} {getattr(exc, 'details', '')}"
check("a module enabled without its dependency is refused", refused, detail)
check("the refusal names the missing dependency", "workforce" in detail, detail)
check("the refusal uses the published code", "module_dependency_unmet" in detail, detail)

# 2. A transitive dependency: payroll needs workforce, leave needs workforce.
try:
    check_module_enablement({"leave", "time_tracking"})
    refused = False
    detail = "the configuration was accepted"
except Exception as exc:  # noqa: BLE001
    refused = True
    detail = f"{getattr(exc, 'code', '')} {getattr(exc, 'details', '')}"
check("a transitive dependency that is off is refused", refused, detail)

# 3. A dependency that is on is accepted.
try:
    check_module_enablement({"leave", "workforce"})
    refused = False
    detail = ""
except Exception as exc:  # noqa: BLE001
    refused = True
    detail = str(exc)
check("a module with its dependency enabled is accepted", not refused, detail)

# 4. A cycle in the preset's own edges is refused.
offending = copy.deepcopy(retail)
for entry in offending["modules"]:
    if entry["key"] == "workforce":
        entry["requires"] = ["leave"]
check("a preset whose dependency edges form a cycle is refused",
      bool(preset_problems(offending)),
      str(preset_problems(offending)[:2]))

# 5. A dependency edge that names a module the preset does not define.
offending = copy.deepcopy(retail)
for entry in offending["modules"]:
    if entry["key"] == "leave":
        entry["requires"] = ["scheduling_that_does_not_exist"]
check("a preset whose dependency edge names nothing is refused",
      bool(preset_problems(offending)),
      str(preset_problems(offending)[:2]))

# 5b. A dependency edge that names a module the product has but the preset
#     does not define. The module that requires it is one the preset does
#     not switch on by default, so the edge itself is the only thing wrong.
offending = copy.deepcopy(retail)
for entry in offending["modules"]:
    if entry["key"] == "payroll":
        entry["requires"] = ["benefits"]
check("a preset whose dependency edge names a module it does not define is refused",
      bool(preset_problems(offending)),
      str(preset_problems(offending)[:2]))

# 6. A module the preset enables by default without the module it needs.
offending = copy.deepcopy(retail)
for entry in offending["modules"]:
    if entry["key"] == "workforce":
        entry["enabled_by_default"] = False
check("a preset that enables a module by default without its dependency is refused",
      bool(preset_problems(offending)),
      str(preset_problems(offending)[:2]))

# 7. The graph of a preset keeps the product's own edges.
if "retail" not in loaded:
    check("the product's own dependency edge is kept in the effective graph",
          False, "retail preset did not load")
    check("the effective graph has no cycle", False, "retail preset did not load")
else:
    graph = ModuleGraph.for_preset(loaded["retail"])
    check("the product's own dependency edge is kept in the effective graph",
          "workforce" in graph.dependencies("leave"),
          str(graph.dependencies("leave")))
    check("the effective graph has no cycle", graph.find_cycle() is None, str(graph.find_cycle()))

# ==========================================================================
print()
print("=" * 68)
print("THE LOADER — it reports what it would change, and changes nothing")
print("=" * 68)

empty_state = TenantState()
if "retail" not in loaded:
    check("the difference against an empty tenant adds the preset's settings",
          False, "retail preset did not load")
else:
    difference = diff_preset(loaded["retail"], empty_state)
    check("the difference against an empty tenant adds the preset's settings",
          len(difference.adds) > 0, str(len(difference.adds)))
    check("the difference against an empty tenant has nothing to overwrite",
          len(difference.overwrites) == 0, str(len(difference.overwrites)))
    check("the difference reports what the preset cannot decide",
          len(difference.undecided) > 0, str(len(difference.undecided)))
    check("the difference reports the modules it would switch on",
          len(difference.modules_to_enable) > 0, str(difference.modules_to_enable))
    check("the difference carries the preset's exclusions",
          len(difference.exclusions) > 0, str(len(difference.exclusions)))

for preset_id in THE_SIX:
    preset = loaded.get(preset_id)
    if preset is None:
        check(f"{preset_id} reports its differences against an empty tenant",
              False, "preset did not load")
        continue
    report = diff_preset(preset, TenantState())
    check(f"{preset_id} reports its differences against an empty tenant",
          len(report.adds) > 0 and len(report.undecided) > 0,
          f"adds={len(report.adds)} undecided={len(report.undecided)}")

# The tenant's own configuration wins.
own_state = TenantState(
    modules={"leave": True, "workforce": True},
    settings={
        "leave.approval_required": {"value": False, "source": "tenant_override"},
        "leave.custom_holiday_calendar": {"value": "closed", "source": "tenant_set"},
    },
)
if "retail" not in loaded:
    check("a setting the tenant changed is reported as an overwrite",
          False, "retail preset did not load")
else:
    difference = diff_preset(loaded["retail"], own_state)
    overwritten = {change.path: change for change in difference.overwrites}
    check("a setting the tenant changed is reported as an overwrite",
          "leave.approval_required" in overwritten,
          str(sorted(overwritten)))
    check("the tenant's value is the one that stands",
          overwritten["leave.approval_required"].tenant_value is False,
          str(overwritten["leave.approval_required"]))
    check("a setting the tenant set where the preset said nothing is left alone",
          len(difference.tenant_only) == 1
          and difference.tenant_only[0].path == "leave.custom_holiday_calendar",
          str([change.path for change in difference.tenant_only]))
    check("the modules the tenant switched on that the preset does not are left alone",
          "leave" not in difference.modules_to_enable,
          str(difference.modules_to_enable))

# ==========================================================================
print()
print("=" * 68)
print("THE PROVENANCE — default, set, overridden")
print("=" * 68)

provenance_state = TenantState(
    modules={"leave": True, "workforce": True},
    settings={
        # Still the preset's proposal: it came from the preset.
        "leave.approval_required": {"value": True, "source": "preset_default"},
        # The customer changed it.
        "leave.allow_negative_balance": {"value": True, "source": "tenant_override"},
        # The customer set something the preset never proposed.
        "leave.some_other_setting": {"value": "x", "source": "tenant_set"},
    },
)
if "retail" not in loaded:
    check("provenance distinguishes preset defaults from tenant values",
          False, "retail preset did not load")
else:
    records = {record.path: record for record in provenance_report(loaded["retail"], provenance_state)}
    check("a value that came from the preset is distinguishable",
          records["leave.approval_required"].state == "preset_default",
          records["leave.approval_required"].state)
    check("a value the customer changed is distinguishable",
          records["leave.allow_negative_balance"].state == "tenant_override",
          records["leave.allow_negative_balance"].state)
    check("a value the customer set is distinguishable",
          records["leave.some_other_setting"].state == "tenant_set",
          records["leave.some_other_setting"].state)
    check("the recorded provenance is honoured rather than derived",
          records["leave.approval_required"].origin == "recorded",
          records["leave.approval_required"].origin)

    # A value that is not recorded is derived by comparison.
    derived = TenantState(
        modules={"leave": True},
        settings={"leave.approval_required": {"value": True}},
    )
    records = {record.path: record for record in provenance_report(loaded["retail"], derived)}
    check("a value that matches the preset is derived as the preset's default",
          records["leave.approval_required"].state == "preset_default",
          records["leave.approval_required"].state)
    check("the derived provenance says where it came from",
          records["leave.approval_required"].origin == "derived",
          records["leave.approval_required"].origin)

    derived = TenantState(
        modules={"leave": True},
        settings={"leave.approval_required": {"value": False}},
    )
    records = {record.path: record for record in provenance_report(loaded["retail"], derived)}
    check("a value that differs from the preset is derived as the customer's change",
          records["leave.approval_required"].state == "tenant_override",
          records["leave.approval_required"].state)

# ==========================================================================
print()
print("=" * 68)
print("THE READINESS CHECK — it reports, and it changes nothing")
print("=" * 68)

db = SessionLocal()
try:
    state = read_state(db)
    facts = read_facts(db)
finally:
    db.close()

if "retail" not in loaded:
    check("the readiness check reports what is configured",
          False, "retail preset did not load")
else:
    report = check_readiness(state, loaded["retail"], facts)
    check("the readiness check reports what is configured",
          len(report.configured) > 0, str(len(report.configured)))
    check("the readiness check reports what is missing",
          len(report.missing) > 0, str(len(report.missing)))
    check("the readiness check reports what is recommended",
          len(report.recommended) > 0, str(len(report.recommended)))
    check("every finding names a fix target",
          all(finding.fix_target for finding in report.findings),
          str([finding.rule_id for finding in report.findings if not finding.fix_target]))
    check("every finding has a severity",
          all(finding.severity in ("blocking", "warning", "info") for finding in report.findings),
          str([finding.severity for finding in report.findings]))
    check("the readiness check finds the missing preset",
          any(finding.rule_id == "setup.preset_selected" for finding in report.missing),
          str([finding.rule_id for finding in report.missing]))
    # The data findings follow the modules that are switched on: a module that
    # is off is not a gap.
    with_modules = check_readiness(
        TenantState(modules={"workforce": True, "leave": True}), loaded["retail"], facts
    )
    check("the readiness check reports on the data of the modules that are on",
          any(finding.rule_id.startswith("data.") for finding in with_modules.findings),
          str([finding.rule_id for finding in with_modules.findings]))
    check("a module that is switched off is not reported as a gap",
          not any(finding.rule_id == "data.shift_templates"
                  for finding in with_modules.findings),
          str([finding.rule_id for finding in with_modules.findings]))

    # An inconsistent configuration is reported as inconsistent.
    broken_state = TenantState(
        preset_id="retail",
        preset_version="1.0.0",
        modules={"leave": True},
        settings={"leave.approval_required": {"value": True}},
    )
    broken = check_readiness(broken_state, loaded["retail"], facts)
    check("a module enabled without its dependency is inconsistent",
          any(finding.rule_id == "modules.dependency_met" for finding in broken.inconsistent),
          str([finding.rule_id for finding in broken.inconsistent]))
    check("an unresolved sentinel is inconsistent",
          any(finding.rule_id == "settings.rule_pack_resolved"
              for finding in check_readiness(
                  TenantState(preset_id="retail", preset_version="1.0.0",
                              modules={"leave": True},
                              settings={"leave.entitlement": {"value": SENTINEL}}),
                  loaded["retail"], facts).inconsistent),
          "no sentinel finding")

# The endpoint writes nothing.
before = db_counts()
response = client.get("/api/v1/onboarding/readiness", headers=ADMIN)
after = db_counts()
check("the readiness endpoint answers", response.status_code == 200, response.text[:200])
check("the readiness endpoint writes nothing to the database", before == after,
      str({k: (before.get(k), after.get(k)) for k in before if before.get(k) != after.get(k)}))

# ==========================================================================
print()
print("=" * 68)
print("THE ENDPOINTS — what they serve, and who may read them")
print("=" * 68)

response = client.get("/api/v1/onboarding/presets", headers=ADMIN)
check("the preset catalogue is served", response.status_code == 200, response.text[:200])
body = response.json()
check("the catalogue holds the six presets", len(body) == 6, str(len(body)))
check("the catalogue reports the version of each preset",
      all(item.get("version") for item in body), str(body[:1]))
check("the catalogue reports the module keys of each preset",
      all(item.get("modules") for item in body), str(body[:1]))

response = client.get("/api/v1/onboarding/presets?industry=retail", headers=ADMIN)
check("the catalogue can be narrowed by business type",
      response.status_code == 200 and len(response.json()) == 1,
      response.text[:200])

response = client.get("/api/v1/onboarding/presets?page=1&page_size=2", headers=ADMIN)
check("the catalogue is paged",
      response.status_code == 200 and len(response.json()) == 2,
      response.text[:200])

response = client.get("/api/v1/onboarding/presets/retail", headers=ADMIN)
check("one preset is served in full", response.status_code == 200, response.text[:200])
detail = response.json()
check("the preset carries its dependency edges",
      isinstance(detail.get("module_dependencies"), dict)
      and detail["module_dependencies"].get("leave"),
      str(detail.get("module_dependencies")))
check("the preset carries its exclusions", len(detail.get("exclusions", [])) > 0,
      str(len(detail.get("exclusions", []))))

response = client.get("/api/v1/onboarding/presets/no-such-preset", headers=ADMIN)
check("an unknown preset is refused with the published code",
      response.status_code == 404
      and response.json().get("error", {}).get("code") == "preset_not_found",
      response.text[:200])

response = client.get("/api/v1/onboarding/presets/retail/diff", headers=ADMIN)
check("the difference report is served", response.status_code == 200, response.text[:200])
difference_body = response.json()
check("the difference report names the preset and its version",
      difference_body.get("preset_id") == "retail" and difference_body.get("preset_version"),
      str(difference_body.get("preset_id")))
check("the difference report carries the provenance",
      len(difference_body.get("provenance", [])) > 0,
      str(len(difference_body.get("provenance", []))))

response = client.get("/api/v1/onboarding/presets", headers=ASSOCIATE)
check("a member of the workforce may not read the catalogue",
      response.status_code == 403, response.text[:200])

response = client.get("/api/v1/onboarding/presets")
check("an unauthenticated caller may not read the catalogue",
      response.status_code == 401, response.text[:200])

response = client.get("/api/v1/onboarding/readiness", headers=ASSOCIATE)
check("a member of the workforce may not read the readiness report",
      response.status_code == 403, response.text[:200])

# ==========================================================================
print()
print("=" * 68)
print("THE TENANT STATE — what the tenant configured is recorded")
print("=" * 68)

db = SessionLocal()
try:
    write_state(
        db,
        preset_id="retail",
        preset_version="1.0.0",
        modules={"leave": True, "workforce": True},
        settings={
            "leave.approval_required": {"value": True, "source": "preset_default"},
            "leave.allow_negative_balance": {"value": True, "source": "tenant_override"},
        },
    )
    db.commit()
    stored = read_state(db)
finally:
    db.close()

check("the chosen preset is recorded", stored.preset_id == "retail", str(stored.preset_id))
check("the version of the chosen preset is recorded",
      stored.preset_version == "1.0.0", str(stored.preset_version))
check("the modules the tenant switched on are recorded",
      stored.enabled_modules() == {"leave", "workforce"}, str(stored.enabled_modules()))
check("the provenance of each setting is recorded",
      stored.source("leave.approval_required") == "preset_default"
      and stored.source("leave.allow_negative_balance") == "tenant_override",
      str(stored.settings))

response = client.get("/api/v1/onboarding/readiness", headers=ADMIN)
check("the readiness report names the chosen preset",
      response.status_code == 200 and response.json().get("preset_id") == "retail",
      response.text[:200])
body = response.json()
check("the chosen preset is reported as configured",
      any(finding["rule_id"] == "setup.preset_selected"
          for finding in body.get("configured", [])),
      str([finding["rule_id"] for finding in body.get("configured", [])]))

response = client.get("/api/v1/onboarding/presets/retail/diff", headers=ADMIN)
body = response.json()
states = {record["path"]: record["state"] for record in body.get("provenance", [])}
check("the difference report tells the preset's default from the customer's change",
      states.get("leave.approval_required") == "preset_default"
      and states.get("leave.allow_negative_balance") == "tenant_override",
      str({k: v for k, v in states.items() if k.startswith("leave.")}))

# ==========================================================================
print("=" * 68)
print("CLIENT REGISTRY REMOVED — single-tenant install answers 404")
print("=" * 68)

# The registry CRUD, /tenants aliases, and by-slug lookup were removed. The
# install serves one org (GET /onboarding-portal/company); the old
# multi-tenant registry surface must answer 404 (no route), never data.
response = client.post("/api/v1/onboarding-portal/clients", headers=ADMIN,
                       json={"name": "Matrix Acme", "slug": "matrix-acme"})
check("the removed registry create answers 404",
      response.status_code == 404, f"got {response.status_code}: {response.text[:200]}")

response = client.get("/api/v1/onboarding-portal/clients", headers=ADMIN)
check("the removed registry list answers 404",
      response.status_code == 404, f"got {response.status_code}: {response.text[:200]}")

response = client.get("/api/v1/onboarding-portal/clients/999999", headers=ADMIN)
check("the removed registry read answers 404",
      response.status_code == 404, f"got {response.status_code}: {response.text[:200]}")

response = client.put("/api/v1/onboarding-portal/clients/999999", headers=ADMIN,
                      json={"status": "Active"})
check("the removed registry update answers 404",
      response.status_code == 404, f"got {response.status_code}: {response.text[:200]}")

response = client.delete("/api/v1/onboarding-portal/clients/999999", headers=ADMIN)
check("the removed registry delete answers 404",
      response.status_code == 404, f"got {response.status_code}: {response.text[:200]}")

response = client.get("/api/v1/onboarding-portal/clients/by-slug/matrix-acme", headers=ADMIN)
check("the removed by-slug lookup answers 404",
      response.status_code == 404, f"got {response.status_code}: {response.text[:200]}")

response = client.get("/api/v1/onboarding-portal/tenants", headers=ADMIN)
check("the removed tenants alias list answers 404",
      response.status_code == 404, f"got {response.status_code}: {response.text[:200]}")

response = client.get("/api/v1/onboarding-portal/tenants/999999", headers=ADMIN)
check("the removed tenants alias read answers 404",
      response.status_code == 404, f"got {response.status_code}: {response.text[:200]}")

response = client.post("/api/v1/onboarding-portal/tenants/999999/provision", headers=ADMIN)
check("the removed tenants lifecycle answers 404",
      response.status_code == 404, f"got {response.status_code}: {response.text[:200]}")

# The single company endpoint replaces the registry for the install's org.
db = SessionLocal()
try:
    from app.models.client_onboarding import Client as _Client
    _company = db.query(_Client).order_by(_Client.id.asc()).first()
    if _company is None:
        _company = _Client(name="Matrix Co", slug="matrix-co", status="Active")
        db.add(_company)
        db.commit()
        db.refresh(_company)
    _company_id = _company.id
finally:
    db.close()

response = client.get("/api/v1/onboarding-portal/company")
check("the single company endpoint answers without auth",
      response.status_code == 200 and response.json().get("id") == _company_id,
      f"got {response.status_code}: {response.text[:200]}")

# AC-5: single-org settings round-trip (read -> update -> read-back).
response = client.get(
    f"/api/v1/onboarding-portal/clients/{_company_id}/settings", headers=ADMIN)
check("company settings read", response.status_code == 200, f"got {response.status_code}")
_before = {row["key"]: row["value"] for row in response.json()}

response = client.put(
    f"/api/v1/onboarding-portal/clients/{_company_id}/settings/company.tagline",
    headers=ADMIN, json={"key": "company.tagline", "value": "Single Tenant Co"})
check("company settings update",
      response.status_code == 200 and response.json().get("value") == "Single Tenant Co",
      f"got {response.status_code}: {response.text[:200]}")

response = client.get(
    f"/api/v1/onboarding-portal/clients/{_company_id}/settings", headers=ADMIN)
_after = {row["key"]: row["value"] for row in response.json()}
check("company settings round-trip reads back the update",
      _after.get("company.tagline") == "Single Tenant Co"
      and all(_after.get(k) == v for k, v in _before.items()),
      str(sorted(_after)))

# ==========================================================================
print()
print("=" * 68)
print(f"==== ONBOARDING SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
