#!/usr/bin/env python3
"""Scan the repository for committed secrets.

Why this exists
---------------
This project shipped a hard-coded default administrator password. It was
printed by the seed script, repeated in the deployment documentation, and it
authenticated against the live production backend until it was rotated. A
code review did not catch it, because it looked like an ordinary constant.

This scan is the control that stops that recurring. It fails the build.

What it looks for
-----------------
1. **A denylist of credentials that have actually been exposed**, held as
   digests so the scanner never stores the credential it is looking for.
   These are always a finding, in any file, including documentation and
   fixtures.
2. **Private key blocks** and known token formats (AWS access key ids,
   GitHub personal access tokens, OpenAI-style keys, Slack tokens, and so
   on).
3. **High-entropy values assigned to secret-looking names**, with an
   allowlist for values that are demonstrably not secrets.

Design rules
------------
* **No network access.** A scanner that phones home is a scanner that can
  leak the repository.
* **Allowlist by exact value, with a reason.** Every exception must say why
  it is safe, so a reviewer can challenge it.
* **False positives are expensive.** A scanner that cries wolf gets disabled.
  The high-entropy check therefore only fires on assignments whose *name*
  looks secret-bearing, and skips obvious placeholders.

Usage
-----
    python ci/secret_scan.py            # scan the working tree
    python ci/secret_scan.py --path DIR # scan a specific directory
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

# --- Configuration -------------------------------------------------------- #

#: Directories that are never scanned.
SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache",
    ".pytest_cache", "dist", "build", ".next", "coverage", ".ruff_cache",
    "frontend/dist", "backend/migrations/versions",
}

#: File extensions that are not scanned. Binary or generated content.
SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".pdf",
    ".woff", ".woff2", ".ttf", ".eot", ".zip", ".gz", ".tar", ".db", ".sqlite",
    ".pyc", ".so", ".dylib", ".dll", ".exe", ".class", ".jar", ".bin",
}

#: Credentials that have been exposed and must never appear again.
#:
#: Stored as digests, never as plaintext. A scanner that keeps the credential
#: it is looking for has published it a second time, and this file is read by
#: everyone who reviews the gate. Each entry is
#: ``(length, first_character, sha256_hex, reason)``.
#:
#: Detection is exact, case-sensitive and offset-independent: every window of
#: the stated length is hashed and compared, so a value embedded in a URL, a
#: fixture or an assignment is found the same way the old substring check
#: found it. The length and the first character are a cheap prefilter; only
#: windows that start with the stored character are hashed.
DENYLIST_DIGESTS: list[tuple[int, str, str, str]] = [
    (
        12,
        "C",
        "9a4aabf0e5cf71cae2cea646613ce7e2a5919fa758e56819704be25a3a2c1f0b",
        "Default administrator password published in the seed script and docs",
    ),
    (
        11,
        "C",
        "08a3d2dc7693d7166eef51ec0194ae6009c7636af128d4a208a14d1b5293c3cd",
        "Default administrator password published in the seed script and docs",
    ),
    (
        20,
        "A",
        "1a5d44a2dca19669d72edf4c4f1c27c4c1ca4b4408fbb17f6ce4ad452d78ddb3",
        "Canonical AWS documentation example access key id",
    ),
]

#: Patterns for credentials that are secret regardless of their name.
TOKEN_PATTERNS: list[tuple[str, str]] = [
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "Private key block"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key id"),
    (r"\bASIA[0-9A-Z]{16}\b", "AWS temporary access key id"),
    (r"\bghp_[A-Za-z0-9]{36}\b", "GitHub personal access token"),
    (r"\bgho_[A-Za-z0-9]{36}\b", "GitHub OAuth token"),
    (r"\bgithub_pat_[A-Za-z0-9_]{50,}\b", "GitHub fine-grained access token"),
    (r"\bsk-[A-Za-z0-9]{20,}\b", "OpenAI-style API key"),
    (r"\bsk-ant-[A-Za-z0-9_-]{20,}\b", "Anthropic API key"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "Slack token"),
    (r"\bAIza[0-9A-Za-z_-]{35}\b", "Google API key"),
    (r"\bya29\.[A-Za-z0-9_-]{20,}\b", "Google OAuth token"),
    (r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "JWT"),
    (r"\b[0-9]{12,19}\b(?=[^\n]*(?:card|credit|CARD|pan|account))", "Possible card number"),
]

#: A name that suggests the value it is assigned is a secret.
#:
#: Matched as a substring of the identifier rather than on word boundaries,
#: so ``DATABASE_PASSWORD`` and ``apiKey`` are both recognised.
SECRET_NAME = re.compile(
    r"(?i)(secret|password|passwd|pwd|token|api[_-]?key|apikey|"
    r"private[_-]?key|access[_-]?key|credential|passphrase)"
)

#: An assignment of a quoted string to a name.
STRING_ASSIGNMENT = re.compile(
    r"([A-Za-z_][A-Za-z0-9_.\-]*)\s*[:=]\s*['\"]([^'\"\n]{8,})['\"]"
)

#: Values that are obviously not real secrets.
#:
#: Two separate tests, because they mean different things:
#:
#: * :data:`PLACEHOLDER_SYMBOL` — the value starts with a character that only
#:   a template would start with (a quote, a brace, a bracket, a placeholder
#:   marker).
#: * :data:`PLACEHOLDER_WORD` — the value *is* one of a small set of words
#:   that stand in for a secret.
#: * :data:`PLACEHOLDER_TEMPLATE` — the value contains template wording.
#:
#: Deliberately *not* treated as a placeholder: values that merely start with
#: "password", "secret" or "token". Those are frequently real credentials
#: (``password123``, ``token_abcdef``) and the length threshold is the right
#: filter for them.
PLACEHOLDER_SYMBOL = re.compile(r"^[\"'`$\[\{<%]")
PLACEHOLDER_WORD = frozenset(
    {
        "none", "null", "nil", "true", "false", "undefined",
        "changeme", "change-me", "change_me",
        "placeholder", "dummy", "redacted", "example", "examples",
        "test", "testing", "local", "dev", "development",
        "todo", "tbd", "unset", "empty", "blank",
    }
)
PLACEHOLDER_TEMPLATE = re.compile(
    r"(?i)(your[_-]?|example|placeholder|changeme|change[_-]?me|"
    r"insert[_-]?here|replace[_-]?me|not[_-]?a[_-]?real|x{3,}|\*{3,}|"
    r"^\$\{|\{\{|<[A-Z_]+>$)"
)

#: Values that are allowed even though they look secret-shaped.
#:
#: Every entry needs a reason. These are local test values, not credentials.
ALLOWLIST: dict[str, str] = {
    "local-test-secret-key-not-for-production-0123456789":
        "Local test key used by the test suites. Never deployed.",
    "smoke-test-secret":
        "Superseded local test key. Not a credential.",
    "dq-test-secret": "Superseded local test key. Not a credential.",
    "import-test-secret": "Superseded local test key. Not a credential.",
    "SchedTestPass123": "Local scheduling test-suite fixture password. Never deployed.",
    "MasterDataPass123": "Local master-data test-suite fixture password. Never deployed.",
    "AuditAdminPass123": "Local audit test-suite fixture password. Never deployed.",
    "AuditAssocPass123": "Local audit test-suite fixture password. Never deployed.",    "ScenarioTestPass123": "Local scenario-builder test-suite fixture password. Never deployed.",
    "security-test-secret": "Superseded local test key. Not a credential.",
    "metrics-test-secret": "Superseded local test key. Not a credential.",
    "visibility-test-secret": "Superseded local test key. Not a credential.",
    "ops-model-test-secret": "Superseded local test key. Not a credential.",
    "AdminPass123": "Local test password in the test suites. Not a credential.",
    "HrPassword12345": "Local test password in the test suites. Not a credential.",
    "EscalatedPass123": "Local test password in the test suites. Not a credential.",
    "Segreg8Review45": "Local test password in the test suites. Not a credential.",
    "WorkerLogin2024": "Local test password in the test suites. Not a credential.",
    "AssociatePass123": "Local test password in the test suites. Not a credential.",
    "Authorized123": "Local test password in the test suites. Not a credential.",
    "AttackerPass123": "Local test password in the test suites. Not a credential.",
    "OpsPass12345": "Local test password in the test suites. Not a credential.",
    "DqPass12345": "Local test password in the test suites. Not a credential.",
    "TestPass12345": "Local test password in the test suites. Not a credential.",
    "KARmathy_E2E_PASSWORD": "Environment variable name, not a value.",
    "KARMATHY_E2E_PASSWORD": "Environment variable name, not a value.",
    "ADMIN_INITIAL_PASSWORD": "Environment variable name, not a value.",
    "ADMIN_RESET_PASSWORD": "Environment variable name, not a value.",
    # --- backend/reset_admin_password_test_suite.py (PS-02) ------------------ #
    # Fixtures for the operator password-reset path. They are created by the
    # suite at run time, are used only against a throwaway SQLite file, and
    # never authenticate against a deployed environment.
    "Operator#Reset2026x":
        "Local test password in reset_admin_password_test_suite.py. "
        "Never deployed.",
    "SomeOtherPassword#1":
        "Local test password in reset_admin_password_test_suite.py. "
        "Never deployed.",
    "HrPassword#2026x":
        "Local test password in reset_admin_password_test_suite.py. "
        "Never deployed.",
    # --- backend/security_test_suite.py (PS-05) ----------------------------- #
    # The role-matrix fixture password. It is created by the suite at run
    # time, authenticates only against the throwaway SQLite file the suite
    # builds, and is never used against a deployed environment.
    "RoleMatrixPass123":
        "Local test password in security_test_suite.py. Never deployed.",
    # --- frontend end-to-end journey fixtures (PS-02) ----------------------- #
    # The Playwright journeys run against a local seeded backend whose
    # accounts are created by the journey itself.
    "E2e!Bootstrap#2026":
        "Local journey password for the seeded end-to-end administrator. "
        "Used only by the local Playwright backend.",
    "E2e!FirstLogin#2026":
        "Local journey password for the seeded first-login account. "
        "Used only by the local Playwright backend.",
    "E2e!Rotated#2026x":
        "Local journey password for the rotated first-login account. "
        "Used only by the local Playwright backend.",
    "E2e!Pending#2026":
        "Local journey password for the pending-change account. "
        "Used only by the local Playwright backend.",
    "PublicContactPass123":
        "Local test password in the public contact suite. Not a credential.",
    "e2e_secret_key_at_least_32_characters_long":
        "Local JWT signing key for the end-to-end backend. The backend "
        "refuses to start with a shorter key; this one is never deployed.",
    # --- backend/leave_test_suite.py (WC-02) --------------------------------- #
    # The password of the local accounts the leave suite creates. It is made
    # at run time, it authenticates against the throwaway SQLite file the
    # suite builds, and it is never deployed.
    "LeaveLedgerPass123":
        "Local test password in the leave suite. Not a credential.",
    # --- 12 CI findings triaged individually (2026-11-22, Final Priority 1) -- #
    # Each value below was a `secret-assignment` finding on the green-CI run.
    # Every one is a local-only fixture or a CSS design token, never a
    # credential. No rule was disabled and no file was exempted: each value
    # is allowlisted by its exact string with its own reason.
    # 1/12 backend/employees_test_suite.py:89 PASSWORD
    "DirectoryPass123":
        "Local test password in employees_test_suite.py. Created at run time, "
        "authenticates only against the throwaway SQLite file. Never deployed.",
    # 2/12 backend/employment_history_test_suite.py:82 PASSWORD
    "EmploymentPass123":
        "Local test password in employment_history_test_suite.py. Created at "
        "run time, authenticates only against the throwaway SQLite file. "
        "Never deployed.",
    # 3/12 backend/legal_entity_test_suite.py:75 PASSWORD
    "LegalEntityPass123":
        "Local test password in legal_entity_test_suite.py. Created at run "
        "time, authenticates only against the throwaway SQLite file. Never "
        "deployed.",
    # 4/12 backend/lp_phase2_access_test_suite.py:37 PASSWORD
    "AccessTest#2026x":
        "Local test password in lp_phase2_access_test_suite.py. Created at "
        "run time, authenticates only against the throwaway SQLite file. "
        "Never deployed.",
    # 5/12 backend/lp_phase2_network_test_suite.py:58 PASSWORD
    "Lockout#Test2026x":
        "Local test password in lp_phase2_network_test_suite.py. Created at "
        "run time, authenticates only against the throwaway SQLite file. "
        "Never deployed.",
    # 6/12 backend/payroll_execution_test_suite.py:22 SECRET_KEY (docstring example)
    "test-secret-key-123456789012345678901234":
        "Documentation example in payroll_execution_test_suite.py docstring. "
        "Shows the env-var shape for a local run; the suite itself uses a "
        "throwaway SQLite file and never deploys this key.",
    # 7/12 frontend/scripts/check-design-alignment.mjs:65 token
    "text-warning-text or badge-amber":
        "CSS design token in check-design-alignment.mjs COLOR_VIOLATIONS. "
        "A Tailwind/design-system class name, not a credential.",
    # 8/12 frontend/scripts/check-design-alignment.mjs:66 token
    "text-success-text or badge-green":
        "CSS design token in check-design-alignment.mjs COLOR_VIOLATIONS. "
        "A Tailwind/design-system class name, not a credential.",
    # 9+10/12 frontend/scripts/check-design-alignment.mjs:67,68 token
    # (one value, two findings: both bg-surface-inset rows)
    "bg-surface-inset":
        "CSS design token in check-design-alignment.mjs COLOR_VIOLATIONS "
        "(lines 67-68). A Tailwind/design-system class name, not a credential.",
    # 11/12 frontend/scripts/check-design-alignment.mjs:70 token
    "border-brand-600":
        "CSS design token in check-design-alignment.mjs COLOR_VIOLATIONS. "
        "A Tailwind/design-system class name, not a credential.",
    # 12/12 frontend/scripts/check-design-alignment.mjs:71 token
    "focus:ring-brand-600 or .input":
        "CSS design token in check-design-alignment.mjs COLOR_VIOLATIONS. "
        "A Tailwind/design-system class name, not a credential.",
    # --- 8 secret-assignment findings triaged individually (2026-11-23) ----- #
    # Every value below is a local-only test-suite fixture password. Each
    # suite builds a throwaway SQLite file under tempfile.mkdtemp, creates
    # its accounts at run time, and never authenticates against a deployed
    # environment. No rule was disabled and no file was exempted: each
    # value is allowlisted by its exact string with its own reason.
    # 1/8 backend/admin_mfa_reset_test_suite.py:64 ADMIN1_PASSWORD
    "ResetAdminPass123!":
        "Local test password in admin_mfa_reset_test_suite.py. Created at "
        "run time, authenticates only against the throwaway SQLite file. "
        "Never deployed.",
    # 2/8 backend/admin_mfa_reset_test_suite.py:65 ADMIN2_PASSWORD
    "ResetAdminTwo123!":
        "Local test password in admin_mfa_reset_test_suite.py. Created at "
        "run time, authenticates only against the throwaway SQLite file. "
        "Never deployed.",
    # 3/8 backend/admin_mfa_reset_test_suite.py:66 HR_PASSWORD
    "ResetHrPass12345!":
        "Local test password in admin_mfa_reset_test_suite.py. Created at "
        "run time, authenticates only against the throwaway SQLite file. "
        "Never deployed.",
    # 4/8 backend/admin_mfa_reset_test_suite.py:67 TARGET_PASSWORD
    "ResetTargetPass123!":
        "Local test password in admin_mfa_reset_test_suite.py. Created at "
        "run time, authenticates only against the throwaway SQLite file. "
        "Never deployed.",
    # 5/8 backend/lifecycle_test_suite.py:80 PASSWORD
    "LifecyclePass123":
        "Local test password in lifecycle_test_suite.py. Created at run "
        "time, authenticates only against the throwaway SQLite file. "
        "Never deployed.",
    # 6/8 backend/security_test_suite.py:1788 _STEP_UP_PASSWORD
    "StepUpPass12345!":
        "Local test password in security_test_suite.py (step-up fixture). "
        "Created at run time, authenticates only against the throwaway "
        "SQLite file. Never deployed.",
    # 7-8/8 backend/startup_test_suite.py:161,210 password (one value, two findings)
    "T7#qW9!zM4$xK2&vB8":
        "Local test password in startup_test_suite.py env-seed fixtures "
        "(lines 161, 210). Used only against a throwaway factory/SQLite "
        "file. Never deployed.",
    # --- backend/mfa_column_regression_test_suite.py:91 PASSWORD ------------ #
    # Local-only fixture password, same precedent as the 8 entries above:
    # created at run time, authenticates only against the throwaway SQLite
    # file the suite builds. Never deployed. No rule disabled, no file
    # exempted: allowlisted by its exact string.
    "MfaColRegPass123!":
        "Local test password in mfa_column_regression_test_suite.py. "
        "Created at run time, authenticates only against the throwaway "
        "SQLite file. Never deployed.",
}

#: Files that are exempt from the high-entropy heuristic because they are
#: expected to contain secret-shaped values (test fixtures, key registries).
HIGH_ENTROPY_EXEMPT_SUFFIX = {".md"}

#: The scanner's own source contains the denylist, so it must not scan itself.
SELF_RELATIVE = "ci/secret_scan.py"


def _git_tracked_files(root: Path) -> list[Path] | None:
    """Files git knows about, or ``None`` when git is unavailable.

    Only tracked files matter: a secret that is not committed cannot be
    leaked by the repository. This also keeps locally-present but
    git-ignored material (Oracle wallet files, ``.env``) out of the scan.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    names = [n for n in result.stdout.split("\0") if n]
    return [root / n for n in names]


def _is_exempt_path(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    parts = set(rel.parts)
    if parts & SKIP_DIRS:
        return True
    return any(str(p) in parts for p in SKIP_DIRS)


def _iter_files(root: Path):
    tracked = _git_tracked_files(root)
    if tracked is not None:
        candidates = tracked
    else:
        candidates = [p for p in root.rglob("*") if p.is_file()]

    for path in candidates:
        if not path.is_file():
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if _is_exempt_path(path, root):
            continue
        if path.is_relative_to(root) and str(path.relative_to(root)) == SELF_RELATIVE:
            continue
        yield path


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _looks_like_placeholder(value: str) -> bool:
    value = value.strip().strip("\"'`")
    if not value:
        return True
    if PLACEHOLDER_SYMBOL.match(value):
        return True
    if value.lower() in PLACEHOLDER_WORD:
        return True
    if PLACEHOLDER_TEMPLATE.search(value):
        return True
    if value in ALLOWLIST:
        return True
    # A value that is mostly the same character is a filler, not a secret.
    if len(set(value)) <= 3:
        return True
    return False


def _denylist_reasons(line: str) -> list[str]:
    """The reasons for every denylisted credential present in ``line``.

    The plaintext is never stored, so it cannot be looked up as a substring.
    Instead every window of the stored length is hashed and compared. The
    first character is a prefilter: a window can only match if it starts
    with the same character, so the hash is computed for a small fraction of
    the windows and the scan stays fast.
    """
    reasons: list[str] = []
    for length, first, digest, reason in DENYLIST_DIGESTS:
        start = line.find(first)
        while start != -1:
            if start + length <= len(line):
                window = line[start : start + length]
                if hashlib.sha256(window.encode("utf-8", "ignore")).hexdigest() == digest:
                    reasons.append(reason)
                    break
            start = line.find(first, start + 1)
    return reasons


def _self_test() -> int:
    """Prove the digest denylist detects a value without storing it.

    The value is generated at run time from a hash, so this file still holds
    no credential. A temporary entry is added to the in-memory list, a line
    that contains the value is scanned, and a line that does not contain it
    must not match. The list is restored afterwards.
    """
    sample = "Zx9!SelfTest-" + hashlib.sha256(b"karmathy-self-test").hexdigest()[:8]
    entry = (
        len(sample),
        sample[0],
        hashlib.sha256(sample.encode()).hexdigest(),
        "self-test value",
    )
    global DENYLIST_DIGESTS
    original = DENYLIST_DIGESTS
    DENYLIST_DIGESTS = [*original, entry]
    try:
        hit = _denylist_reasons(f'password = "{sample}"')
        miss = _denylist_reasons('password = "a-different-value"')
        embedded = _denylist_reasons(f"postgres://user:{sample}@host/db")
        if not hit or not embedded:
            print("secret_scan: self-test FAILED - the digest denylist did not detect the value")
            return 1
        if miss:
            print("secret_scan: self-test FAILED - a different value matched")
            return 1
        print("secret_scan: self-test passed - the digest denylist detects a value it does not store.")
        return 0
    finally:
        DENYLIST_DIGESTS = original


def scan(root: Path) -> list[tuple[str, int, str, str]]:
    """Return findings as ``(path, line number, rule, detail)``."""
    findings: list[tuple[str, int, str, str]] = []

    for path in _iter_files(root):
        text = _read(path)
        if not text:
            continue
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        lines = text.splitlines()

        for number, line in enumerate(lines, 1):
            for reason in _denylist_reasons(line):
                findings.append((rel, number, "denylist", reason))

            for pattern, label in TOKEN_PATTERNS:
                for match in re.finditer(pattern, line):
                    value = match.group(0)
                    if value in ALLOWLIST:
                        continue
                    # A JWT in a test fixture or a documentation example is
                    # not a leaked credential, but a real one is. Flag it and
                    # let the allowlist decide.
                    findings.append((rel, number, "token-pattern", f"{label}: {value[:12]}..."))

            if path.suffix.lower() in HIGH_ENTROPY_EXEMPT_SUFFIX:
                continue

            for match in STRING_ASSIGNMENT.finditer(line):
                name, value = match.group(1), match.group(2)
                if not SECRET_NAME.search(name):
                    continue
                if value in ALLOWLIST or _looks_like_placeholder(value):
                    continue
                if len(value) < 16 or value.startswith(("http", "/", "$", "{", "[")):
                    continue
                if value.count(" ") > 3:
                    continue
                findings.append(
                    (rel, number, "secret-assignment",
                     f"value assigned to {name!r} looks like a credential")
                )

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan the repository for secrets")
    parser.add_argument(
        "--path",
        default=str(Path(__file__).resolve().parent.parent),
        help="directory to scan (default: the repository root)",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="prove the digest denylist works, without storing a credential",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"secret_scan: {root} does not exist", file=sys.stderr)
        return 2

    findings = scan(root)

    if not findings:
        print("secret_scan: no secrets found.")
        return 0

    print(f"secret_scan: {len(findings)} finding(s):", file=sys.stderr)
    for rel, number, rule, detail in findings:
        print(f"  {rel}:{number}: [{rule}] {detail}", file=sys.stderr)
    print(
        "\nIf a finding is a false positive, add the exact value to ALLOWLIST in "
        "ci/secret_scan.py with a reason. Do not disable the rule.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
