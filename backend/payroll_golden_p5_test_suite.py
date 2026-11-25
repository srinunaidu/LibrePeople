"""Payroll golden P5 suite — FY26-27 skeleton placeholders, engine branch, no activation.

P5 proves five things, all without inventing a statutory value:

1. **The schema only annotates.** ``contracts/rules/rule-pack.schema.json``
   ``golden_cases`` carries the TEST-ONLY placeholder convention in its
   description; its type, items ref and the ``golden_case`` case_id pattern
   are unchanged.
2. **The skeleton appends structure only.** The FY26-27 skeleton ships
   exactly 14 TEST-ONLY placeholder golden cases (``gc-fy2627-p5-01..14``),
   every expected amount is 0, every case carries ``placeholder: true``,
   every rate/value is 0 and thresholds/overtime numerics are null. Status
   stays ``pending_verification`` with null verification.
3. **The engine takes the placeholder branch deterministically.**
   ``run_golden_cases`` passes all 14 skeleton cases without calculating
   (identical message on repeat runs), while the 11 FY25-26 cases still
   calculate line for line and a direct calculation on the skeleton is
   still refused.
4. **Nothing activates.** The resolver still returns the verified FY25-26
   pack through 2026-03-31 and ``pack=None`` (pending, no fallback) from
   2026-04-01.
5. **FY25-26 is untouched.** Still verified v1.0.0 with 11 cases, no
   TEST-ONLY marker, stable content sha, Decimal HALF_UP money.

Run:  python payroll_golden_p5_test_suite.py
"""
from __future__ import annotations

import json
import os
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = BACKEND_ROOT.parent / "contracts" / "rules" / "rule-pack.schema.json"
SHIPPED_PACK_DIR = BACKEND_ROOT.parent / "rule_packs"
SKELETON_PATH = BACKEND_ROOT / "rule_packs" / "in-standard-fy2627-skeleton.json"
FY2526_PATH = BACKEND_ROOT / "rule_packs" / "in-standard.json"

os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["RULE_PACK_DIR"] = str(SHIPPED_PACK_DIR)
os.environ["LOG_LEVEL"] = "CRITICAL"

from app.rules.engine import calculate_payslip_from_pack, run_golden_cases  # noqa: E402
from app.rules.loader import load_rule_pack, validate_against_schema  # noqa: E402
from app.rules.money import money  # noqa: E402
from app.rules.resolver import resolve_rule_pack  # noqa: E402

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


CASE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

print("=" * 68)
print("P5-1 — the schema only annotates (no logic change)")
print("=" * 68)

schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
gc_prop = schema["properties"]["golden_cases"]
check("schema golden_cases description annotates TEST-ONLY placeholders",
      "TEST-ONLY placeholder" in gc_prop.get("description", ""),
      gc_prop.get("description", "")[:120])
check("schema golden_cases stays an array of golden_case",
      gc_prop.get("type") == "array"
      and gc_prop.get("items", {}).get("$ref") == "#/$defs/golden_case",
      json.dumps({k: gc_prop.get(k) for k in ("type", "items")})[:160])
golden_def = schema["$defs"]["golden_case"]["properties"]["case_id"]
check("schema golden_case case_id pattern untouched",
      golden_def.get("pattern") == "^[a-z0-9]+(?:-[a-z0-9]+)*$",
      repr(golden_def.get("pattern")))

print("=" * 68)
print("P5-2 — the skeleton appends 14 TEST-ONLY placeholders, values stay 0")
print("=" * 68)

skel_data = json.loads(SKELETON_PATH.read_text(encoding="utf-8"))
skel_errors = validate_against_schema(skel_data)
check("skeleton schema-validates with placeholders", skel_errors == [], "; ".join(skel_errors)[:200])
check("skeleton stays pending with null verification",
      skel_data.get("status") == "pending_verification" and skel_data.get("verification") is None,
      f"status={skel_data.get('status')!r} verification={skel_data.get('verification')!r}")
check("skeleton version and window untouched (2026-04-01 open-ended)",
      skel_data.get("version") == "0.1.0-fy2627-skeleton"
      and skel_data.get("effective_from") == "2026-04-01"
      and skel_data.get("effective_to") is None,
      f"{skel_data.get('version')} {skel_data.get('effective_from')}..{skel_data.get('effective_to')}")
cases = skel_data.get("golden_cases", [])
check("skeleton ships exactly 14 placeholder cases", len(cases) == 14, f"got {len(cases)}")
ids = [c.get("case_id", "") for c in cases]
check("placeholder case_ids unique, patterned, P5-prefixed",
      len(set(ids)) == 14 and all(CASE_ID_RE.match(i) for i in ids)
      and all(i.startswith("gc-fy2627-p5-") for i in ids),
      ",".join(sorted(ids))[:200])
check("every placeholder description carries TEST-ONLY",
      all("TEST-ONLY placeholder" in (c.get("description") or "") for c in cases))


def _is_zero(v) -> bool:
    try:
        return Decimal(str(v)) == 0
    except Exception:
        return False


check("every placeholder expected is zero amounts + placeholder:true",
      all(
          c.get("expected", {}).get("placeholder") is True
          and _is_zero(c.get("expected", {}).get("gross"))
          and _is_zero(c.get("expected", {}).get("net"))
          and _is_zero(c.get("expected", {}).get("total_deductions"))
          and c.get("expected", {}).get("pay_floor_check") == "pass"
          for c in cases
      ))
check("every placeholder input is zero amounts",
      all(
          all(_is_zero(v) or (isinstance(v, str) and v in ("monthly", "KA", "MH", "WB"))
              for v in (c.get("input") or {}).values())
          for c in cases
      ))

nonzero_rates: list[str] = []
for table_name, table in skel_data.get("rate_tables", {}).items():
    for entry in table.get("entries", []):
        if entry.get("rate") is not None and not _is_zero(entry["rate"]):
            nonzero_rates.append(f"{table_name}/{entry.get('code')}")
    for code, val in (table.get("values") or {}).items():
        if not _is_zero(val.get("value")):
            nonzero_rates.append(f"{table_name}/{code}")
check("skeleton rates and keyed values are all 0 (no statutory values)",
      nonzero_rates == [], ",".join(nonzero_rates)[:200])
threshold_numerics = {k: v for k, v in skel_data.get("thresholds", {}).items()
                      if k not in ("minimum_wage_unit",) and v is not None}
overtime_numerics = {k: v for k, v in skel_data.get("overtime", {}).items()
                     if k != "rules" and v is not None}
check("skeleton thresholds/overtime numerics stay null (structure only)",
      threshold_numerics == {} and overtime_numerics == {},
      f"thresholds={threshold_numerics} overtime={overtime_numerics}"[:200])

print("=" * 68)
print("P5-3 — the engine takes the placeholder branch deterministically")
print("=" * 68)

skel = load_rule_pack(SKELETON_PATH)
run1 = run_golden_cases(skel)
run2 = run_golden_cases(skel)
check("engine passes all 14 skeleton placeholders", len(run1) == 14 and all(p for _, p, _ in run1),
      str([(c, p, m) for c, p, m in run1 if not p])[:200])
check("placeholder runs are deterministic (repeat identical)",
      run1 == run2)
check("placeholder messages never claim calculation",
      all("PLACEHOLDER" in m and "not calculated" in m for _, _, m in run1),
      str([m for _, _, m in run1[:2]])[:200])
fy2526 = load_rule_pack(FY2526_PATH)
fy_results = run_golden_cases(fy2526)
check("FY25-26 11 real cases still calculate line for line",
      len(fy_results) == 11 and all(p for _, p, _ in fy_results),
      str([(c, m) for c, p, m in fy_results if not p])[:200])
check("no FY25-26 case touches the placeholder branch",
      all("PLACEHOLDER" not in m for _, _, m in fy_results))
try:
    calculate_payslip_from_pack(pack=skel, base_salary=Decimal("50000"), pay_frequency="monthly")
    check("direct calculation on the pending skeleton is refused", False, "no refusal raised")
except ValueError as exc:
    check("direct calculation on the pending skeleton is refused",
          "not verified" in str(exc), str(exc)[:160])

print("=" * 68)
print("P5-4 — nothing activates (resolver still gates on 2026-04-01)")
print("=" * 68)

r_mar = resolve_rule_pack("IN", date(2026, 3, 31))
check("IN 2026-03-31 resolves verified FY25-26",
      r_mar.pack is not None and r_mar.pack.meta.version == "1.0.0"
      and r_mar.pack_status == "verified",
      f"status={r_mar.pack_status}")
r_apr = resolve_rule_pack("IN", date(2026, 4, 1))
check("IN 2026-04-01 resolves pack None (pending, no fallback)",
      r_apr.pack is None and r_apr.pack_status == "pending_verification",
      f"status={r_apr.pack_status}")
r_dec = resolve_rule_pack("IN", date(2026, 12, 1))
check("IN 2026-12-01 still resolves pack None (no activation)",
      r_dec.pack is None and r_dec.pack_status == "pending_verification",
      f"status={r_dec.pack_status}")

print("=" * 68)
print("P5-5 — FY25-26 untouched, money untouched")
print("=" * 68)

fy_data = json.loads(FY2526_PATH.read_text(encoding="utf-8"))
check("FY25-26 verified v1.0.0 with 11 cases, window intact",
      fy_data.get("status") == "verified" and fy_data.get("version") == "1.0.0"
      and len(fy_data.get("golden_cases", [])) == 11
      and fy_data.get("effective_from") == "2025-04-01"
      and fy_data.get("effective_to") == "2026-03-31",
      f"{fy_data.get('status')} {fy_data.get('version')} n={len(fy_data.get('golden_cases', []))}")
check("FY25-26 carries no TEST-ONLY marker and no placeholder flag",
      all("TEST-ONLY" not in (c.get("description") or "") for c in fy_data["golden_cases"])
      and all(c.get("expected", {}).get("placeholder") is not True for c in fy_data["golden_cases"]))
again = load_rule_pack(FY2526_PATH)
check("FY25-26 content_sha stable across loads", again.content_sha == fy2526.content_sha)
check("money rounds half up (2.345 -> 2.35)", money("2.345") == Decimal("2.35"), str(money("2.345")))
check("no shipped backend pack carries a TEST-ONLY pack id",
      all("test-only" not in p.read_text(encoding="utf-8").lower()
          or p.name == "in-standard-fy2627-skeleton.json"
          for p in (BACKEND_ROOT / "rule_packs").glob("*.json")))

print()
print("=" * 68)
print(f"==== PAYROLL GOLDEN P5: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
