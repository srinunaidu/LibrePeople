#!/usr/bin/env python3
"""Hardening tests for ci/check_licences.py (report-only, Tier 2).

- verdict() reaches all four statuses; UNVERIFIED/missing never Confirmed.
- --check-only exits 0; --strict exits non-zero on current inventory.
- strict_failure() exits 0 only with zero Blocked/Unknown rows+findings.
- Output deterministic: repeated runs byte-identical (stdout sorted).

Run: python -m unittest ci.test_check_licences -v
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "ci" / "check_licences.py"

sys.path.insert(0, str(REPO / "ci"))
import check_licences as cl  # noqa: E402


def run_script(*args, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    return proc


class VerdictFourStatusTest(unittest.TestCase):
    def test_all_four_reachable(self):
        self.assertEqual(cl.verdict("MIT")[0], cl.CONFIRMED)
        self.assertEqual(cl.verdict("CC-BY-4.0")[0], cl.REVIEW)
        self.assertEqual(cl.verdict("GPL-3.0-only")[0], cl.BLOCKED)
        self.assertEqual(cl.verdict("MPL-2.0")[0], cl.BLOCKED)
        self.assertEqual(cl.verdict("UNVERIFIED")[0], cl.UNKNOWN)
        self.assertEqual(cl.verdict(None)[0], cl.UNKNOWN)
        self.assertEqual(cl.verdict("")[0], cl.UNKNOWN)

    def test_unverified_never_confirmed(self):
        for raw in (None, "", "   ", "UNVERIFIED", "MISSING", "missing"):
            status, _ = cl.verdict(raw)
            self.assertNotEqual(status, cl.CONFIRMED, f"{raw!r} must never be Confirmed")
            self.assertEqual(status, cl.UNKNOWN)


class StrictExitCodeTest(unittest.TestCase):
    def test_check_only_exits_zero(self):
        proc = run_script("--check-only")
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])

    def test_strict_exits_nonzero_on_current_inventory(self):
        proc = run_script("--strict", "--check-only")
        self.assertNotEqual(proc.returncode, 0, proc.stdout[-2000:])
        self.assertIn("Blocked: 3", proc.stdout)
        self.assertIn("Unknown: 133", proc.stdout)

    def test_strict_only_flag_also_nonzero(self):
        proc = run_script("--strict", "--check-only")
        self.assertEqual(proc.returncode, 1, proc.stdout[-2000:])

    def test_strict_failure_logic(self):
        ok_rows = [
            {"package": "a", "version": "1", "status": cl.CONFIRMED},
            {"package": "b", "version": "1", "status": cl.REVIEW},
        ]
        ok_findings = [{"check": "notice", "status": cl.REVIEW, "detail": "x"}]
        self.assertFalse(cl.strict_failure(ok_rows, ok_findings))
        self.assertFalse(cl.strict_failure([], []))
        bad_rows = [{"package": "c", "version": "1", "status": cl.BLOCKED}]
        self.assertTrue(cl.strict_failure(bad_rows, ok_findings))
        unk_rows = [{"package": "d", "version": "1", "status": cl.UNKNOWN}]
        self.assertTrue(cl.strict_failure(unk_rows, []))
        bad_findings = [{"check": "sbom-freshness", "status": cl.BLOCKED, "detail": "y"}]
        self.assertTrue(cl.strict_failure(ok_rows, bad_findings))
        unk_findings = [{"check": "notice", "status": cl.UNKNOWN, "detail": "z"}]
        self.assertTrue(cl.strict_failure([], unk_findings))

    def test_help_documents_flags(self):
        proc = run_script("--help")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--check-only", proc.stdout)
        self.assertIn("--strict", proc.stdout)


class DeterminismTest(unittest.TestCase):
    def test_repeated_check_only_byte_identical(self):
        first = run_script("--check-only")
        second = run_script("--check-only")
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(first.stdout, second.stdout)

    def test_json_report_deterministic_with_fixed_epoch(self):
        import json
        import tempfile

        env = {"SOURCE_DATE_EPOCH": "1793030400"}
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            r1 = run_script("--output-dir", d1, env_extra=env)
            r2 = run_script("--output-dir", d2, env_extra=env)
            self.assertEqual(r1.returncode, 0, r1.stderr[-2000:])
            self.assertEqual(r2.returncode, 0, r2.stderr[-2000:])
            j1 = (Path(d1) / "licensing-compliance-report.json").read_bytes()
            j2 = (Path(d2) / "licensing-compliance-report.json").read_bytes()
            self.assertEqual(j1, j2)
            data = json.loads(j1)
            self.assertEqual(
                list(data.keys()), ["findings", "meta", "summary", "verdicts"]
            )
            # sorted verdict rows
            keys = [
                (v["package"].lower(), v["version"], v["scope"])
                for v in data["verdicts"]
            ]
            self.assertEqual(keys, sorted(keys))

    def test_sbom_freshness_compares_package_version_sets(self):
        rows = cl.load_inventory()
        status, detail, info = cl.sbom_freshness(rows)
        self.assertIn(status, (cl.CONFIRMED, cl.REVIEW))
        self.assertIn("sbom_files", info)


if __name__ == "__main__":
    unittest.main()
