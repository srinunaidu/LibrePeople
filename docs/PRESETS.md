# PRESETS.md — the six business presets

**Owner:** Onboarding & Config · **Contract:** `contracts/rules/preset.schema.json` ·
**Code:** `backend/app/core/presets/` · **Suite:** `backend/onboarding_test_suite.py`

A preset is a **versioned, reusable starting configuration** that a customer
selects during onboarding. It is a document, not a decision.

Three rules hold for every preset, and the server enforces all three:

1. **A preset carries no statutory value.** Every slot that can only be filled
   from a jurisdiction rule pack holds the literal `REQUIRES_RULE_PACK`. A tax
   rate, a contribution percentage, a leave entitlement, a minimum wage and a
   break length are all in that category. The loader refuses a preset that
   states one.
2. **A preset only offers modules the product has.** The check is against the
   running application: a module whose routers are not registered is not
   offered.
3. **The customer's own configuration always wins.** The loader reports what a
   preset *would* change before anything changes, and the readiness check
   changes nothing at all.

---

## The six presets

| Preset | For | Modules it offers | Version |
|---|---|---|---|
| [`retail`](../backend/app/core/presets/data/retail.json) | A shop that trades long hours and runs shifts | 11 | 1.0.0 |
| [`construction`](../backend/app/core/presets/data/construction.json) | Site work, crews and a programme of work | 12 | 1.0.0 |
| [`hospitality`](../backend/app/core/presets/data/hospitality.json) | A venue that works around the clock | 12 | 1.0.0 |
| [`healthcare_clinic`](../backend/app/core/presets/data/healthcare_clinic.json) | A clinic rostered by appointments | 13 | 1.0.0 |
| [`light_manufacturing`](../backend/app/core/presets/data/light_manufacturing.json) | A plant working to a production plan | 12 | 1.0.0 |
| [`generic_office`](../backend/app/core/presets/data/generic_office.json) | An office that works a normal week | 12 | 1.0.0 |

Every preset defines the same elements, because the onboarding journey reads
the same elements of each of them:

| Element | Where it lives in the document |
|---|---|
| The modules and their dependency edges | `modules` |
| The per-module configuration | `configuration` |
| Departments, job families and roles | `organisation_templates` |
| Shift templates and working patterns | `configuration.scheduling.shift_templates` |
| Leave types and their accrual parameters | `configuration.leave.leave_types` |
| Dashboards, indicators and action queues | `dashboards` |
| Forecast drivers and the data they need | `forecast_drivers` |
| The import templates that apply | `import_templates` |
| The setup validations | `validations` |
| What the preset does not decide | `exclusions` |

---

## What each preset decides, and what it leaves to the customer

### `retail`

**Decides.** A shop floor that clocks in on a phone with the site geofence on;
a trading week that starts on Monday with a five-minute clock-in tolerance and
rounding to the nearest five minutes; four shift patterns — an early opening
shift, a full trading day, a late close and the weekend cover — published a
week at a time; four leave types (annual, sick, family and unpaid) with a
manager's approval; eleven modules from workforce records to recruiting; the
store structure (store operations, customer service, supply chain and store
management) with three job families and five roles; three dashboards (trading
day, labour this week, leave and cover) with seven indicators and three action
queues; the forecast drivers (trading hours, seasonal footfall, staff
availability) and the data they need; five import templates; five setup
validations.

**Leaves to the customer.** Everything jurisdictional — the leave entitlement
and its accrual, the tax and the contributions, the minimum wage, the break
length and the working-time limits, the notice period, the background-check
consent scope, the retention periods — plus the pay cycle and the currency,
which the preset carries as a monthly cycle and a placeholder currency for the
customer to confirm. The trading hours and the shop calendar are the shop's
own.

### `construction`

**Decides.** Site work recorded on a phone with a wide site geofence (250 m),
a ten-minute clock-in tolerance and rounding to the nearest fifteen minutes;
four site patterns (day crew, early shift, late shift, weekend cover) with a
site induction required of everyone on them; the commercial, site-management,
plant-and-equipment and support structure with four job families and six
roles; learning switched on, because a site induction and a certification have
to be recorded before somebody is rostered; the forecast drivers (programme of
work, seasonality, staff availability).

**Leaves to the customer.** The site safety rules and the statutory training, the
production working-time limits, and every jurisdictional item above. The
preset names the slots and says so in its exclusions.

### `hospitality`

**Decides.** A trading week that starts on Sunday, because a venue's week runs
with the trade; a mobile clock-in with a 200 m venue geofence; four patterns
(early, mid, late and the housekeeping shift), the late one flagged as an
overnight shift; a fortnightly pay cycle; shift swaps enabled for the team;
learning on, for the service training and the licences a role needs.

**Leaves to the customer.** The split-shift and night-work rules and the
premium that attracts, the treatment of tips and service charge, and every
jurisdictional item above.

### `healthcare_clinic`

**Decides.** A badge clock-in at the clinic entrance with a 120 m geofence and
no employee self-editing of the recorded hours, because the clinic's record is
its own; four clinic sessions (morning clinic, afternoon clinic, late clinic
and the administrative day); compliance switched on, because the rules the
clinic is measured against and the exceptions that have to be closed belong
with the practice manager; learning on, for the clinical training a regulator
asks for.

**Leaves to the customer.** The professional registration a role needs and the
scope of practice, the confidentiality of patient information, and every
jurisdictional item above.

### `light_manufacturing`

**Decides.** A badge clock-in at the plant gate with a 200 m geofence, a
ten-minute clock-in tolerance and rounding to the nearest fifteen minutes;
four patterns including the overnight shift for a plant that runs continuously
and the maintenance window when the lines are down; learning on, for the
machine inductions and the certifications an operator has to hold; the
production, quality, maintenance, planning and support structure with four job
families and six roles.

**Leaves to the customer.** The production working-time rules, the health and
safety requirements, and every jurisdictional item above.

### `generic_office`

**Decides.** A web clock-in with no geofence, because an office that does not
work by the hour may leave the time capture switched off and use the
timesheet instead; a five-minute clock-in tolerance; four leave types; a
standard working day as the working pattern, offered by the scheduling module
but not switched on by default; learning and performance on; no scheduling
module switched on by default, because an office works to a job description
rather than to a rota.

**Leaves to the customer.** The office calendar and the core hours, and every
jurisdictional item above.

---

## The dependency graph

The graph is a directed acyclic graph over the module keys. Its edges are the
union of two sources:

* **the product's own edges**, in `backend/app/core/presets/modules.py` — for
  example `time` requires `time_tracking`, and every module that works on
  people requires `workforce`;
* **the preset's own edges**, on each module entry in the document.

A preset may add an edge. It may not remove one: the product's edge is always
in the effective graph.

The server refuses four things, and each refusal is tested:

| Refused | Error code |
|---|---|
| A module enabled while a module it requires is not | `module_dependency_unmet`, with the missing dependency named |
| A preset whose dependency edges form a cycle | `validation_error` |
| A dependency edge that names a module the preset does not define | `validation_error` |
| A module the application does not serve | `validation_error` |

---

## The provenance

Every setting a tenant holds has a provenance, and the difference report shows
it per value:

| State | Meaning |
|---|---|
| `preset_default` | The tenant's value is the preset's proposal, unchanged. |
| `tenant_override` | The tenant's value differs: the tenant changed it. |
| `tenant_set` | The tenant has a value the preset did not propose. |
| `not_set` | The tenant has not set the value. |
| `unresolved_rule_pack` | The preset proposed the sentinel; only a verified rule pack fills it. |

A provenance the tenant **recorded** is honoured; one the server **derived** by
comparing the value with the preset is marked as such. A customer who overrode
a preset is a customer whose configuration is theirs, and the product says so
without being asked.

---

## What the server serves

| Operation | What it does |
|---|---|
| `GET /api/v1/onboarding/presets` | The catalogue, paged, filterable by business type. |
| `GET /api/v1/onboarding/presets/{preset_id}` | One preset in full, with its dependency edges. |
| `GET /api/v1/onboarding/presets/{preset_id}/diff` | What the preset would change, and the provenance of every setting. |
| `GET /api/v1/onboarding/readiness` | What is configured, missing, inconsistent and recommended. |

All four are read-only and are restricted to the administrative roles. The
contract for them is `contracts/openapi/onboarding.yaml`.

---

## How a preset is read

```python
from app.core.presets import load_preset, diff_preset, read_state

preset = load_preset("retail")          # validates; raises on a broken preset
state = read_state(db)                  # what the deployment has configured
difference = diff_preset(preset, state) # what it would change; changes nothing
```

`load_preset` also accepts a document, which is how a preset held in the
tenant's own configuration is read: it is held to exactly the same rules, and
it may not carry a statutory number either.
