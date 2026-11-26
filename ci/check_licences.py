#!/usr/bin/env python3
"""Report-only licensing compliance check (PREPARED-ONLY, Tier 2, slice 3).

Inventories direct dependencies from ``backend/requirements.txt`` and
``frontend/package.json``, lists transitive dependencies via
``docs/legal/dependency-licence-inventory.json``, flags missing/restricted
licence metadata, checks NOTICE presence, validates SBOM freshness against
``docs/legal/sbom-*.json``, detects proprietary-risk files via the
``.gitignore`` allowlist, and emits per-dependency
``Confirmed / Review required / Blocked / Unknown`` verdicts plus a
markdown + JSON report.

Report-only: by default this script NEVER fails the build. It always exits 0
so the caller workflow stays non-blocking (``continue-on-error`` as well).
Pass ``--strict`` for the documented future enforcement path: exit 1 when
any Blocked/Unknown verdict row or any Blocked/Unknown repo-level finding
is present, exit 0 only when zero Blocked/Unknown rows AND zero
Blocked/Unknown findings. ``--strict`` is for future use only and MUST NOT
be enabled in CI without explicit human approval
(see ``docs/legal/compliance-ci.md`` enforcement policy). It never marks
``UNVERIFIED`` / missing licence metadata as ``Confirmed``.

Output is deterministic: verdict rows, findings, and non-confirmed listings
are sorted, JSON is emitted with stable (sorted) keys, and SBOM freshness
compares the inventory package@version set against the ``docs/legal/sbom-*.json``
component set. The ``meta.generated_utc`` timestamp honours ``SOURCE_DATE_EPOCH``
when set, so repeated runs with the same environment are byte-identical.

The script prints only package names/versions/licences and findings text;
it never prints secret values (keys, tokens, passwords).

Usage:
    python ci/check_licences.py --check-only
    python ci/check_licences.py --strict --check-only   # future enforcement dry-run (exit 1 on Blocked/Unknown)
    python ci/check_licences.py --output-dir /tmp/compliance-out

Exit codes:
    default / --check-only      always 0 (report-only; findings never fail the build)
    --strict [--check-only]     0 only when zero Blocked/Unknown verdict rows and
                                zero Blocked/Unknown findings; 1 otherwise
    usage / inventory errors    2 (argparse usage errors exit 2; unreadable inventory exits non-zero)
"""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INVENTORY = REPO / "docs" / "legal" / "dependency-licence-inventory.json"
SBOM_GLOB = str(REPO / "docs" / "legal" / "sbom-*.json")
REQUIREMENTS = REPO / "backend" / "requirements.txt"
PACKAGE_JSON = REPO / "frontend" / "package.json"
GITIGNORE = REPO / ".gitignore"

CONFIRMED = "Confirmed"
REVIEW = "Review required"
BLOCKED = "Blocked"
UNKNOWN = "Unknown"

#: Verified permissive licences compatible with the proposed AGPL-3.0-or-later
#: posture (all GPL/AGPL-compatible). Anything not on this list is never
#: Confirmed: restricted licences are Blocked, everything else needs review.
#:
#: Allowlist rationale (triage 2026-11-26, report-only; membership unchanged):
#: - MIT / Apache-2.0 / BSD-2-Clause / BSD-3-Clause / 0BSD / BlueOak-1.0.0:
#:   OSI-approved permissive licences with no copyleft condition on combination;
#:   GPL-family compatible, so no conflict with a future AGPL-3.0-or-later grant.
#: - ISC: functionally equivalent to MIT/BSD-2-Clause (permission + warranty
#:   disclaimer); accepted as permissive here but ISC `lucide-react` still carries
#:   an L11 clearance row until counsel confirms frontend-bundle compatibility.
#: - NOT on this list by design: (MPL/LGPL/GPL/AGPL (file-/library-level copyleft
#:   triggers clearance, e.g. MPL-2.0 axe-core L10); UPL-1.0 (Oracle patent/term
#:   review, L9); CC-BY-4.0 / Python-2.0 (posture review, Review required);
#:   UNVERIFIED/missing (Unknown, never Confirmed without registry/lockfile
#:   evidence). No entry suppresses Unknown/Blocked: every non-Confirmed row is
#:   still listed with its verdict in the report.
CONFIRMED_LICENCES = {
    "MIT",
    "Apache-2.0",
    "ISC",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "0BSD",
    "BlueOak-1.0.0",
}

#: Recognised non-copyleft licences that still need a human posture review
#: (content licence applied to code; GPL-incompatible legacy licence).
REVIEW_LICENCES = {
    "CC-BY-4.0",
    "Python-2.0",
}

#: Substring markers (lowercase) for restricted licences: strong/weak copyleft
#: and commercial/proprietary/unknown identifiers. Matched rows are Blocked
#: pending legal clearance. Covers GPL/AGPL/LGPL/MPL/commercial/unknown.
BLOCKED_MARKERS = (
    "agpl",
    "gpl",  # also matches lgpl
    "mpl",
    "commercial",
    "proprietary",
    "unknown",
)

#: Tracked-file basename/extension markers that almost certainly mean secret
#: material. Tracked matches are Blocked findings (report-only).
SECRET_BLOBS = (
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".wallet",
)

NOTICE_CANDIDATES = ("NOTICE", "NOTICE.md", "NOTICE.txt")


def verdict(licence: str | None) -> tuple[str, str]:
    """Return (status, reason) for a raw licence string. Never Confirmed
    unless the licence is a verified allowlist member."""
    raw = (licence or "").strip()
    if not raw or raw == "UNVERIFIED" or raw.upper() == "MISSING":
        return UNKNOWN, "licence metadata missing or UNVERIFIED; verification pending"
    if raw in CONFIRMED_LICENCES:
        return CONFIRMED, "verified permissive licence, compatible with proposed posture"
    if raw in REVIEW_LICENCES:
        return REVIEW, "recognised licence needing posture review (see compliance-ci.md)"
    lowered = raw.lower()
    if any(marker in lowered for marker in BLOCKED_MARKERS):
        return BLOCKED, "restricted licence (copyleft/commercial/unknown); legal clearance required"
    return REVIEW, f"unrecognised licence identifier {raw!r}; human identification required"


def load_inventory() -> list[dict]:
    with open(INVENTORY, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise SystemExit(f"error: {INVENTORY} is not a JSON list")
    return data


def generated_utc_now() -> str:
    """UTC timestamp honouring SOURCE_DATE_EPOCH for reproducible reports."""
    import os
    epoch = os.environ.get("SOURCE_DATE_EPOCH", "").strip()
    if epoch.isdigit():
        dt = datetime.datetime.fromtimestamp(int(epoch), tz=datetime.timezone.utc)
    else:
        dt = datetime.datetime.now(datetime.timezone.utc)
    return dt.isoformat(timespec="seconds")


def sort_verdict_rows(verdict_rows: list[dict]) -> list[dict]:
    """Deterministic ordering: (package, version, scope), case-insensitive."""
    return sorted(
        verdict_rows,
        key=lambda r: (
            str(r.get("package", "")).lower(),
            str(r.get("version", "")),
            str(r.get("scope", "")),
        ),
    )


def sort_findings(findings: list[dict]) -> list[dict]:
    """Deterministic ordering: (check, status, detail)."""
    return sorted(
        findings,
        key=lambda f: (
            str(f.get("check", "")),
            str(f.get("status", "")),
            str(f.get("detail", "")),
        ),
    )


def strict_failure(verdict_rows: list[dict], findings: list[dict]) -> bool:
    """True when --strict must exit non-zero: any Blocked/Unknown verdict row
    or any Blocked/Unknown repo-level finding."""
    if any(r.get("status") in (BLOCKED, UNKNOWN) for r in verdict_rows):
        return True
    return any(f.get("status") in (BLOCKED, UNKNOWN) for f in findings)


def requirement_names() -> list[str]:
    names: list[str] = []
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[=<>;\s\[]", line, maxsplit=1)[0].strip().lower()
        if name:
            names.append(name)
    return names


def package_names() -> list[str]:
    pkg = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    deps = dict(pkg.get("dependencies", {}))
    deps.update(pkg.get("devDependencies", {}))
    return sorted(deps)


def direct_coverage(rows: list[dict]) -> tuple[list[str], dict[str, int]]:
    """Every manifest direct dep must have a scope==direct inventory row."""
    direct = {str(r.get("package", "")).lower() for r in rows if r.get("scope") == "direct"}
    findings: list[str] = []
    counts = {"requirements": 0, "package_json": 0, "missing": 0}
    if REQUIREMENTS.exists():
        reqs = requirement_names()
        counts["requirements"] = len(reqs)
        for name in reqs:
            if name not in direct:
                counts["missing"] += 1
                findings.append(f"backend requirement `{name}` has no scope==direct inventory row")
    if PACKAGE_JSON.exists():
        pkgs = package_names()
        counts["package_json"] = len(pkgs)
        for name in pkgs:
            if name.lower() not in direct:
                counts["missing"] += 1
                findings.append(f"frontend dependency `{name}` has no scope==direct inventory row")
    return findings, counts


def sbom_freshness(rows: list[dict]) -> tuple[str, str, dict]:
    """SBOM component set must equal the inventory package@version set.

    Stale (or missing) SBOM => Review required, never a silent pass.
    """
    invset = {(str(r.get("package")), str(r.get("version"))) for r in rows}
    sbom_files = sorted(glob.glob(SBOM_GLOB))
    info = {"sbom_files": [Path(p).name for p in sbom_files], "components": 0}
    if not sbom_files:
        return REVIEW, "no docs/legal/sbom-*.json found; SBOM freshness unknown", info
    compset: set[tuple[str, str]] = set()
    for path in sbom_files:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for comp in data.get("components", []):
            compset.add((str(comp.get("name")), str(comp.get("version"))))
    info["components"] = len(compset)
    info["inventory_rows"] = len(rows)
    info["inventory_unique"] = len(invset)
    only_inv = sorted(invset - compset)
    only_sbom = sorted(compset - invset)
    info["only_in_inventory"] = only_inv[:20]
    info["only_in_sbom"] = only_sbom[:20]
    if only_inv or only_sbom:
        return (
            REVIEW,
            f"SBOM stale: {len(only_inv)} inventory rows missing from SBOM, "
            f"{len(only_sbom)} SBOM components missing from inventory",
            info,
        )
    return (
        CONFIRMED,
        f"SBOM fresh: all {len(rows)} inventory rows "
        f"({len(invset)} unique package@version) covered by {len(sbom_files)} SBOM file(s)",
        info,
    )


def notice_check() -> tuple[str, str]:
    for name in NOTICE_CANDIDATES:
        if (REPO / name).exists():
            return CONFIRMED, f"root {name} present"
    return (
        REVIEW,
        "no root NOTICE file; third-party attributions live in "
        "docs/legal/third-party-licences.md - confirm NOTICE sufficiency with legal",
    )


def tracked_files() -> list[str] | None:
    try:
        out = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return [line for line in out.stdout.splitlines() if line.strip()]


def proprietary_scan() -> tuple[str, list[str], dict]:
    """Gitignore-aware proprietary allowlist scan (report-only).

    Tier 1 (Blocked): tracked secret blobs (*.key, *.pem, ...).
    Tier 2 (Review required): tracked files matching a .gitignore allowlist
    pattern (e.g. backend/wallet/*, *credential*) - tracked despite the
    allowlist, so confirm intentional and secret-free.
    """
    tracked = tracked_files()
    if tracked is None:
        return UNKNOWN, ["cannot enumerate tracked files (git ls-files failed)"], {}
    try:
        out = subprocess.run(
            ["git", "check-ignore", "--no-index", "--stdin"],
            input="\n".join(tracked),
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return UNKNOWN, ["cannot evaluate .gitignore allowlist (git check-ignore failed)"], {}
    ignored = {line for line in out.stdout.splitlines() if line.strip()}
    blocked = sorted(p for p in ignored if p.lower().endswith(SECRET_BLOBS))
    review = sorted(p for p in ignored if p not in set(blocked))
    info = {"tracked": len(tracked), "allowlist_overrides": len(ignored)}
    if blocked:
        return BLOCKED, [f"tracked secret-blob file: {p}" for p in blocked], info
    if review:
        return (
            REVIEW,
            [f"tracked despite .gitignore allowlist (confirm intentional, secret-free): {p}" for p in review],
            info,
        )
    return CONFIRMED, [], info


def render_stdout(summary: dict[str, int], total: int, n_direct: int, n_trans: int,
                  findings: list[dict], non_confirmed: list[dict]) -> str:
    lines = [
        "Licensing compliance (report-only, PREPARED-ONLY) - no enforcement by default; --strict exits 1 on Blocked/Unknown",
        f"Inventory: {total} rows ({n_direct} direct, {n_trans} transitive) via {INVENTORY.name}",
        "",
        "Per-dependency verdicts:",
        f"  {CONFIRMED}: {summary[CONFIRMED]}",
        f"  {REVIEW}: {summary[REVIEW]}",
        f"  {BLOCKED}: {summary[BLOCKED]}",
        f"  {UNKNOWN}: {summary[UNKNOWN]}",
        "",
        "Status legend: Confirmed = verified permissive, compatible with proposed posture; "
        "Review required = needs human legal review; "
        "Blocked = restricted (GPL/AGPL/LGPL/MPL/commercial/unknown) or secret-blob, must not ship until cleared; "
        "Unknown = licence metadata missing/UNVERIFIED or check unevaluable. "
        "UNVERIFIED is never Confirmed.",
        "",
    ]
    if non_confirmed:
        lines.append("Non-confirmed dependencies (package@version -> status: reason):")
        for row in non_confirmed:
            lines.append(
                f"  {row['package']}@{row['version']} [{row['scope']}] -> "
                f"{row['status']}: {row['reason']}"
            )
        lines.append("")
    else:
        lines.append("All dependencies Confirmed.")
        lines.append("")
    lines.append("Repo-level findings:")
    if findings:
        for finding in findings:
            lines.append(f"  [{finding['status']}] {finding['check']}: {finding['detail']}")
    else:
        lines.append("  (none)")
    return "\n".join(lines) + "\n"


def render_markdown(summary: dict[str, int], total: int, rows: list[dict],
                    findings: list[dict], meta: dict) -> str:
    out = [
        "# Licensing compliance report (report-only, PREPARED-ONLY)",
        "",
        f"Generated (UTC): {meta['generated_utc']} on branch `{meta['branch']}`.",
        "No enforcement: findings never block merges. Human gate: no push/merge to main, no release.",
        "",
        "## Summary",
        "",
        f"Inventory rows: {total} ({meta['n_direct']} direct, {meta['n_transitive']} transitive).",
        "",
        "| Status | Count |",
        "| --- | --- |",
        f"| {CONFIRMED} | {summary[CONFIRMED]} |",
        f"| {REVIEW} | {summary[REVIEW]} |",
        f"| {BLOCKED} | {summary[BLOCKED]} |",
        f"| {UNKNOWN} | {summary[UNKNOWN]} |",
        "",
        "## Repo-level findings",
        "",
    ]
    if findings:
        for finding in findings:
            out.append(f"- **[{finding['status']}]** {finding['check']}: {finding['detail']}")
    else:
        out.append("- (none)")
    out += ["", "## Non-confirmed dependencies", ""]
    non_confirmed = [r for r in rows if r["status"] != CONFIRMED]
    if non_confirmed:
        out += ["| Package | Version | Scope | Licence | Status | Reason |",
                "| --- | --- | --- | --- | --- | --- |"]
        for row in non_confirmed:
            out.append(
                f"| {row['package']} | {row['version']} | {row['scope']} | "
                f"{row['licence']} | {row['status']} | {row['reason']} |"
            )
    else:
        out.append("All dependencies Confirmed.")
    out += ["", "See `licensing-compliance-report.json` for the full per-dependency table.",
            "Triage guide: `docs/legal/compliance-ci.md`.",
            ""]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report-only licensing compliance check.")
    parser.add_argument("--check-only", action="store_true",
                        help="stdout only; write no report files; exit 0 "
                             "unless --strict is also passed")
    parser.add_argument("--strict", action="store_true",
                        help="future enforcement path only (requires human approval): "
                             "exit 1 when any Blocked/Unknown verdict row or any "
                             "Blocked/Unknown finding is present; exit 0 only when "
                             "zero Blocked/Unknown rows and zero Blocked/Unknown findings")
    parser.add_argument("--output-dir", default=".",
                        help="directory for licensing-compliance-report.{md,json} (default: cwd)")
    args = parser.parse_args()

    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"], cwd=REPO,
            capture_output=True, text=True, timeout=30,
        ).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        branch = "unknown"

    rows = load_inventory()
    verdict_rows: list[dict] = []
    for row in rows:
        status, reason = verdict(row.get("licence"))
        verdict_rows.append({
            "package": row.get("package"),
            "version": row.get("version"),
            "scope": row.get("scope"),
            "licence": row.get("licence"),
            "status": status,
            "reason": reason,
        })

    summary = {CONFIRMED: 0, REVIEW: 0, BLOCKED: 0, UNKNOWN: 0}
    for row in verdict_rows:
        summary[row["status"]] += 1
    n_direct = sum(1 for r in verdict_rows if r.get("scope") == "direct")
    n_trans = sum(1 for r in verdict_rows if r.get("scope") == "transitive")

    findings: list[dict] = []

    missing_direct, cov = direct_coverage(rows)
    if missing_direct:
        for item in missing_direct:
            findings.append({"check": "direct-coverage", "status": REVIEW, "detail": item})
    else:
        findings.append({
            "check": "direct-coverage", "status": CONFIRMED,
            "detail": f"all {cov['requirements']} requirements pins + "
                      f"{cov['package_json']} package.json deps have scope==direct inventory rows",
        })

    sbom_status, sbom_detail, _sbom_info = sbom_freshness(rows)
    findings.append({"check": "sbom-freshness", "status": sbom_status, "detail": sbom_detail})

    notice_status, notice_detail = notice_check()
    findings.append({"check": "notice", "status": notice_status, "detail": notice_detail})

    prop_status, prop_details, _prop_info = proprietary_scan()
    if prop_details:
        for detail in prop_details:
            findings.append({"check": "proprietary-allowlist", "status": prop_status, "detail": detail})
    else:
        findings.append({
            "check": "proprietary-allowlist", "status": prop_status,
            "detail": "no tracked files match secret-blob or .gitignore allowlist patterns",
        })

    non_confirmed = sort_verdict_rows([r for r in verdict_rows if r["status"] != CONFIRMED])
    findings = sort_findings(findings)
    verdict_rows = sort_verdict_rows(verdict_rows)
    sys.stdout.write(render_stdout(summary, len(verdict_rows), n_direct, n_trans, findings, non_confirmed))

    if not args.check_only:
        meta = {
            "generated_utc": generated_utc_now(),
            "branch": branch,
            "posture": "AGPL-3.0-or-later PROPOSED; no effective licensing; PREPARED-ONLY report-only",
            "n_direct": n_direct,
            "n_transitive": n_trans,
            "strict": bool(args.strict),
        }
        outdir = Path(args.output_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "licensing-compliance-report.json").write_text(
            json.dumps({"meta": meta, "summary": summary,
                        "findings": findings, "verdicts": verdict_rows},
                       indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (outdir / "licensing-compliance-report.md").write_text(
            render_markdown(summary, len(verdict_rows), verdict_rows, findings, meta),
            encoding="utf-8",
        )
    if args.strict and strict_failure(verdict_rows, findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
