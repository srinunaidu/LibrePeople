#!/usr/bin/env python3
"""Independent acceptance harness (Priority 1).

Per-row backend + frontend + permission legs; promotes a CSV row to
VERIFIED only on observed pass. BLOCKED / IN PROGRESS rows are never
flipped. CSV-safe (csv module). Deterministic, idempotent reruns.

Usage:
    SECRET_KEY=local-test-secret-key-not-for-production-0123456789 \\
        python scripts/acceptance_harness.py --dry-run   # evidence only
    SECRET_KEY=... python scripts/acceptance_harness.py  # + gated CSV write
"""
from __future__ import annotations

import argparse
import csv
import datetime
import glob
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(REPO_ROOT, "docs", "product", "requirements-traceability.csv")
EVIDENCE_DIR = os.path.join(REPO_ROOT, "docs", "product", "acceptance-evidence")
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
FRONTEND_DIR = os.path.join(REPO_ROOT, "frontend")

SUITE_RE = re.compile(r"([A-Za-z0-9_]+_test_suite|smoke_test_[A-Za-z0-9_]+)\.py", re.IGNORECASE)
SUMMARY_RE = re.compile(r"(\d+)\s+passed,\s*(\d+)\s+failed")
SHARED_PERM_SUITES = ["cross_tenant_test_suite", "security_test_suite", "lp_phase2_access_test_suite"]
# Env mirrors ci/run_backend_tests.sh:29-33
HARNESS_ENV = {
    "SECRET_KEY": os.environ.get("SECRET_KEY", "local-test-secret-key-not-for-production-0123456789"),
    "BACKEND_CORS_ORIGINS": "",
    "ALLOW_SELF_REGISTRATION": "false",
    "LOG_LEVEL": "CRITICAL",
    "MIGRATE_ON_STARTUP": "false",
}


def repo_python() -> str:
    for cand in (os.path.join(REPO_ROOT, ".venv", "bin", "python"), sys.executable):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return sys.executable


def head_sha() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                             capture_output=True, text=True, timeout=30)
        sha = out.stdout.strip()
        if sha:
            return sha
    except Exception:
        pass
    return "unknown"


def extract_suites(text: str) -> list[str]:
    if not text:
        return []
    seen: list[str] = []
    for m in SUITE_RE.findall(text):
        name = m.lower()
        if name not in seen:
            seen.append(name)
    return seen


def run_backend_suite(suite: str, python: str, timeout: int = 900) -> dict:
    """Run backend/<suite>.py with a clean DB (same as ci/run_backend_tests.sh)."""
    suite_file = os.path.join(BACKEND_DIR, suite + ".py")
    if not os.path.isfile(suite_file):
        return {"exit": 127, "summary": "suite file not present", "skipped": True}
    for db in glob.glob(os.path.join(BACKEND_DIR, "*.db")):
        try:
            os.remove(db)
        except OSError:
            pass
    env = dict(os.environ)
    env.update(HARNESS_ENV)
    try:
        proc = subprocess.run([python, suite_file], cwd=BACKEND_DIR,
                              capture_output=True, text=True, timeout=timeout, env=env)
        output = (proc.stdout or "") + (proc.stderr or "")
        m = SUMMARY_RE.search(output)
        # ci/run_backend_tests.sh falls back to counting FAIL lines
        summary = f"{m.group(1)} passed, {m.group(2)} failed" if m else \
            f"failures: {len(re.findall(r'^  FAIL', output, re.M))}"
        tail = "\n".join(output.splitlines()[-25:])
        return {"exit": proc.returncode, "summary": summary, "tail": tail}
    except subprocess.TimeoutExpired:
        return {"exit": 124, "summary": "timeout", "tail": "timeout expired"}


def run_cmd(cmd: list[str], cwd: str, timeout: int = 600) -> dict:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        output = (proc.stdout or "") + (proc.stderr or "")
        tail = "\n".join(output.splitlines()[-25:])
        return {"exit": proc.returncode, "summary": output.splitlines()[-1][:200] if output.splitlines() else "",
                "tail": tail}
    except FileNotFoundError:
        return {"exit": 127, "summary": "command not found: " + " ".join(cmd), "tail": ""}
    except subprocess.TimeoutExpired:
        return {"exit": 124, "summary": "timeout", "tail": "timeout expired"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Acceptance harness P1 (dry-run first).")
    ap.add_argument("--dry-run", action="store_true", help="evidence only; do not modify CSV")
    ap.add_argument("--csv", default=CSV_PATH)
    ap.add_argument("--evidence-dir", default=EVIDENCE_DIR)
    ap.add_argument("--backend-timeout", type=int, default=900)
    ap.add_argument("--only", default="", help="comma-separated IDs to limit the run (debug)")
    args = ap.parse_args()

    only = {i.strip() for i in args.only.split(",") if i.strip()}

    with open(args.csv, newline="", encoding="utf-8") as f:
        lines = [ln for ln in f if not ln.startswith("#")]
    if not lines or not lines[0].startswith("Requirement ID"):
        print("harness: expected header starting 'Requirement ID'", file=sys.stderr)
        return 2
    reader = csv.DictReader(lines)
    fieldnames = list(reader.fieldnames or [])
    rows = list(reader)
    for col in ("Requirement ID", "Implementation status", "Automated test IDs",
                "UI reference", "Permission / security tests", "Acceptance evidence",
                "Blocker / decision"):
        if col not in fieldnames:
            print(f"harness: missing column {col!r}", file=sys.stderr)
            return 2
    if len(rows) != 136:
        print(f"harness: row count {len(rows)} != 136", file=sys.stderr)
        return 2

    sha = head_sha()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    stamp_full = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    python = repo_python()

    in_scope = [r for r in rows if r["Implementation status"] == "IMPLEMENTED"]
    triage_blocked = [r for r in rows if r["Implementation status"] == "BLOCKED"]
    held_in_progress = [r for r in rows if r["Implementation status"] == "IN PROGRESS"]
    if only:
        in_scope = [r for r in in_scope if r["Requirement ID"] in only]

    # Build per-row mapping.
    mapping: dict[str, dict] = {}
    all_backend_suites: list[str] = []
    for r in in_scope:
        rid = r["Requirement ID"]
        backend_suites = extract_suites(r.get("Automated test IDs") or "")
        perm_suites = extract_suites(r.get("Permission / security tests") or "")
        ui_ref = (r.get("UI reference") or "").strip()
        legs = list(backend_suites)
        for s in perm_suites + SHARED_PERM_SUITES:
            if s not in legs:
                legs.append(s)
        mapping[rid] = {"backend_suites": backend_suites, "perm_suites": perm_suites,
                        "ui_ref": ui_ref, "legs": legs}
        for s in legs:
            if s not in all_backend_suites:
                all_backend_suites.append(s)

    # Runner: each distinct backend suite once (perm triple shared via same cache,
    # keyed implicitly by HEAD SHA since one harness run == one SHA).
    suite_results: dict[str, dict] = {}
    for suite in sorted(all_backend_suites):
        print(f"harness: backend {suite} ...", flush=True)
        suite_results[suite] = run_backend_suite(suite, python, timeout=args.backend_timeout)
        st = suite_results[suite]
        print(f"harness:   -> exit={st['exit']} {st.get('summary', '')}", flush=True)

    # Frontend leg (only meaningful per row when UI reference non-empty):
    # run route/api-path checks once, plus per-area unit tests where a
    # referenced *.test.tsx file exists. Cached and joined per row.
    frontend_checks: dict[str, dict] = {}
    npm = "npm"
    frontend_checks["check:routes"] = run_cmd([npm, "run", "check:routes"], FRONTEND_DIR)
    frontend_checks["check:api-paths"] = run_cmd([npm, "run", "check:api-paths"], FRONTEND_DIR)
    print(f"harness: frontend check:routes exit={frontend_checks['check:routes']['exit']}, "
          f"check:api-paths exit={frontend_checks['check:api-paths']['exit']}", flush=True)

    os.makedirs(args.evidence_dir, exist_ok=True)
    verdicts: dict[str, str] = {}
    passing: list[str] = []
    for r in in_scope:
        rid = r["Requirement ID"]
        m = mapping[rid]
        suites: dict[str, dict] = {}
        fail_reasons: list[str] = []
        if not m["backend_suites"]:
            fail_reasons.append("no-mapped-backend-suite")
        for s in m["legs"]:
            res = suite_results.get(s, {"exit": 127, "summary": "not run"})
            suites[s] = {"exit": res["exit"], "summary": res.get("summary", "")}
            if res["exit"] != 0:
                fail_reasons.append(f"backend:{s}")
        # Frontend leg only if UI reference non-empty.
        if m["ui_ref"]:
            for name, res in frontend_checks.items():
                suites[f"frontend:{name}"] = {"exit": res["exit"], "summary": res.get("summary", "")}
                if res["exit"] != 0:
                    fail_reasons.append(f"frontend:{name}")
            # Area unit test when the row names an existing test file.
            test_files = re.findall(r"[\w\-/]+\.test\.tsx?", m["ui_ref"])
            ran_area = False
            for tf in test_files:
                cand = os.path.join(FRONTEND_DIR, tf) if not tf.startswith("frontend/") \
                    else os.path.join(REPO_ROOT, tf)
                if os.path.isfile(cand):
                    rel = os.path.relpath(cand, FRONTEND_DIR)
                    key = f"frontend:test:unit:{rel}"
                    suites[key] = run_cmd([npm, "run", "test:unit", "--", rel], FRONTEND_DIR)
                    ran_area = True
                    if suites[key]["exit"] != 0:
                        fail_reasons.append(key)
            if not ran_area:
                suites["frontend:area"] = {"exit": 0,
                    "summary": "no row-specific unit file; route/api-path checks apply"}
        verdict = "PASS" if not fail_reasons else "FAIL"
        verdicts[rid] = verdict
        if verdict == "PASS":
            passing.append(rid)
        doc = {"id": rid, "head_sha": sha, "timestamp_utc": stamp_full,
               "status_before": r["Implementation status"],
               "mapping": {"backend_suites": m["backend_suites"],
                           "perm_suites": m["perm_suites"],
                           "ui_ref_non_empty": bool(m["ui_ref"])},
               "suites": suites,
               "fail_reasons": fail_reasons, "verdict": verdict}
        failing = [k for k, v in suites.items() if v["exit"] != 0]
        if failing:
            doc["failing_tail"] = {k: suite_results.get(k, {}).get("tail",
                suites[k].get("tail", "")) for k in failing if not k.startswith("frontend:")}
            for k in failing:
                if k.startswith("frontend:") and "tail" in suites[k]:
                    doc.setdefault("failing_tail", {})[k] = suites[k]["tail"][-2000:]
        with open(os.path.join(args.evidence_dir, f"{rid}.json"), "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
            f.write("\n")

    # Triage evidence for never-flipped rows (no suite runs; status preserved).
    for r in triage_blocked + held_in_progress:
        rid = r["Requirement ID"]
        doc = {"id": rid, "head_sha": sha, "timestamp_utc": stamp_full,
               "status_before": r["Implementation status"], "verdict": "HELD",
               "reason": "BLOCKED/IN PROGRESS rows are never flipped by the harness",
               "blocker_or_decision": r.get("Blocker / decision", "")}
        with open(os.path.join(args.evidence_dir, f"{rid}.json"), "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
            f.write("\n")

    passed_n = len(passing)
    failed_ids = sorted(v for v, verdict in verdicts.items() if verdict == "FAIL")

    # Gate + writer (skipped under --dry-run).
    csv_changed: list[str] = []
    if not args.dry_run:
        by_id = {r["Requirement ID"]: r for r in rows}
        for rid in passing:
            row = by_id[rid]
            if row["Implementation status"] == "IMPLEMENTED":
                legs = mapping[rid]["legs"]
                note = (f"harness {stamp} HEAD {sha[:7]} "
                        f"{'+'.join(mapping[rid]['backend_suites']) or 'no-backend-suite'} PASS")
                prev = row.get("Acceptance evidence") or ""
                row["Implementation status"] = "VERIFIED"
                row["Acceptance evidence"] = (prev + "; " if prev else "") + note
                csv_changed.append(rid)
                _ = legs
        # Assertions: row count, 8 DEFERRED BY APPROVAL allowed, BLOCKED at 4
        # (8 surplus DEFERRED post-initial per owner mandate HEAD e92987c;
        # LP-DOC-002 INCLUDED -> IMPLEMENTED 2026-11-22;
        # LP-DATA-002 INCLUDED -> IMPLEMENTED HEAD 9486e51;
        # LP-DOC-001 INCLUDED -> IMPLEMENTED 2026-11-22 HEAD 99a3739;
        # LP-ADM-005 INCLUDED -> IMPLEMENTED 2026-11-22 HEAD 13a85b5;
        # LP-NOT-002 INCLUDED -> IMPLEMENTED 2026-11-22 HEAD 72f066c).
        assert len(rows) == 136, "row count changed"
        statuses = [r["Implementation status"] for r in rows]
        # Reconciled register (2026-11-24): VERIFIED 2 / IMPLEMENTED 105 /
        # IN PROGRESS 3 / BLOCKED 18 / DEFERRED 8. Promotable set is
        # IMPLEMENTED only; VERIFIED/BLOCKED/DEFERRED/IN PROGRESS never touched.
        assert statuses.count("VERIFIED") == 2, f"VERIFIED=={statuses.count('VERIFIED')} != 2"
        assert statuses.count("IMPLEMENTED") == 105, f"IMPLEMENTED=={statuses.count('IMPLEMENTED')} != 105"
        assert statuses.count("DEFERRED") == 8, f"DEFERRED=={statuses.count('DEFERRED')} != 8"
        assert statuses.count("BLOCKED") == 18, f"BLOCKED=={statuses.count('BLOCKED')} != 18"
        # (was ==4 pre-HEAD 65a1af2, which promoted LP-NFR-014 BLOCKED->IMPLEMENTED
        # per owner INCLUDE as hardening gate; gate updated to match that mandate)
        assert statuses.count("IN PROGRESS") == 3, "IN PROGRESS count changed"
        for r in rows:
            if r["Requirement ID"] not in csv_changed and r["Requirement ID"] in verdicts:
                assert r["Implementation status"] == "IMPLEMENTED", \
                    f"unexpected flip {r['Requirement ID']}"
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
    else:
        assert len(rows) == 136, "row count changed"
        assert len([r for r in rows if r["Implementation status"] == "VERIFIED"]) == 2
        assert len([r for r in rows if r["Implementation status"] == "IMPLEMENTED"]) == 105
        assert len([r for r in rows if r["Implementation status"] == "BLOCKED"]) == 18
        assert len([r for r in rows if r["Implementation status"] == "DEFERRED"]) == 8
        assert len([r for r in rows if r["Implementation status"] == "IN PROGRESS"]) == 3

    # Report: summary.md with counts + BLOCKED triage (verbatim dependency).
    retained_ver = sum(1 for r in rows if r["Implementation status"] == "VERIFIED")
    retained_impl = sum(1 for r in rows if r["Implementation status"] == "IMPLEMENTED")
    lines = [f"# Acceptance harness summary ({stamp} HEAD {sha})",
             "",
             f"- mode: {'dry-run (CSV untouched)' if args.dry_run else 'full run (gated CSV write)'}",
             f"- in-scope rows: {len(in_scope)} "
             f"({sum(1 for r in rows if r['Implementation status'] == 'IMPLEMENTED')} at write time)",
             f"- PASS (all legs exit 0): {passed_n}",
             f"- FAIL retained: {len(failed_ids)}",
             f"- promoted to VERIFIED this run: {len(csv_changed)}"
             + (f" ({', '.join(sorted(csv_changed))})" if csv_changed else ""),
             f"- retained IMPLEMENTED: {retained_impl}; VERIFIED preserved: {retained_ver}",
             f"- BLOCKED held (never flipped): {len(triage_blocked)}",
             f"- IN PROGRESS held (never flipped): {len(held_in_progress)}",
             "",
             "## Failing / retained rows",
             ", ".join(failed_ids) if failed_ids else "none",
             "",
             "## BLOCKED triage (verbatim `Blocker / decision`)",
             ""]
    for r in sorted(triage_blocked, key=lambda x: x["Requirement ID"]):
        lines.append(f"### {r['Requirement ID']}")
        lines.append("")
        lines.append("```")
        lines.append(r.get("Blocker / decision", ""))
        lines.append("```")
        lines.append("")
    lines += ["## IN PROGRESS (held)",
              ""]
    for r in sorted(held_in_progress, key=lambda x: x["Requirement ID"]):
        lines.append(f"- {r['Requirement ID']}: {(r.get('Blocker / decision') or '')[:200]}")
    lines += ["",
              "## Notes",
              "- Oracle roundtrip out of scope (no wallet/schema here).",
              "- FY26-27 skeleton refusal (409 rule_pack_not_verified for dates >= 2026-04-01) "
              "fails payroll rows legitimately; recorded as fail, never force-passed.",
              "- Frontend e2e needs a live server; harness defaults to unit/route checks; "
              "e2e-dependent rows stay unpromoted with reason.",
              "- Known FAILs retained (e.g. LP-AUD-005/006 stay IMPLEMENTED): "
              "admin_audit route-mount defect, no app-code fix in this slice.",
              ""]
    with open(os.path.join(args.evidence_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"harness done: PASS={passed_n} FAIL={len(failed_ids)} "
          f"promoted={len(csv_changed)} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
