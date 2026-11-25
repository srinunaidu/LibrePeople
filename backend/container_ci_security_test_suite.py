"""Container and CI configuration — security regression suite.

Pins three decisions in the deployment files so they cannot quietly drift:

* The backend container start never runs the administrator password reset.
  Starting a container must not change an existing administrator's password.
* The backend Dockerfile and every CI job use Python 3.11.
* The reset script stays available for manual operator use (it is not
  deleted), but is not referenced by the container command.

This suite reads the files on disk. It does not start Docker or a database.

Run with:

    python container_ci_security_test_suite.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_ROOT.parent
DOCKERFILE = BACKEND_ROOT / "Dockerfile"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
RESET_SCRIPT = BACKEND_ROOT / "scripts" / "reset_admin_password.py"

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


def dockerfile_cmd(text: str) -> str:
    """Return the final CMD instruction line(s), joining continuation lines.

    The Dockerfile also has a HEALTHCHECK with its own CMD probe; the first
    CMD in the file is that probe, not the container start. The gate pins
    the start command, so the last CMD is the one that matters.
    """
    lines = text.splitlines()
    # Find the last top-level CMD (the container start), not the HEALTHCHECK probe.
    last_idx = max(
        (i for i, line in enumerate(lines) if line.strip().upper().startswith("CMD ")),
        default=-1,
    )
    if last_idx == -1:
        return ""
    lines = lines[last_idx:]
    out: list[str] = []
    capturing = False
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("CMD "):
            capturing = True
        if capturing:
            out.append(stripped)
            if not stripped.endswith("\\"):
                break
    return "\n".join(out)


def main() -> int:
    print("container / CI security suite")

    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    cmd = dockerfile_cmd(dockerfile)

    # --- Item 7: the start command must not reset the admin password -------
    check("Dockerfile has a CMD instruction", bool(cmd), "no CMD found")
    check(
        "CMD does not invoke reset_admin_password",
        "reset_admin_password" not in cmd,
        f"CMD still runs the reset: {cmd}",
    )
    check(
        "no ENTRYPOINT runs the reset",
        not any(
            "reset_admin_password" in line
            for line in dockerfile.splitlines()
            if line.strip().upper().startswith(("ENTRYPOINT", "RUN ", "ENV ", "CMD "))
        ),
        "a non-comment instruction references reset_admin_password",
    )
    check(
        "CMD still migrates and starts uvicorn",
        "scripts.migrate upgrade" in cmd and "uvicorn app.main:app" in cmd,
        f"CMD: {cmd}",
    )
    check(
        "reset script is kept for manual operator use",
        RESET_SCRIPT.is_file(),
        "scripts/reset_admin_password.py was removed",
    )

    # --- Item 7: Python 3.11 everywhere --------------------------------------
    check(
        "Dockerfile base image is python:3.11",
        re.search(r"^FROM\s+python:3\.11", dockerfile, re.M) is not None,
        "FROM line is not python:3.11",
    )

    ci_text = CI_WORKFLOW.read_text(encoding="utf-8")
    pins = re.findall(r'python-version:\s*"?([0-9.]+)"?', ci_text)
    check("CI declares at least one python-version", bool(pins), "no python-version found")
    check(
        "every CI python-version is 3.11",
        pins and all(p == "3.11" for p in pins),
        f"found pins: {sorted(set(pins))}",
    )
    check(
        "CI contains no 3.12 pin",
        "3.12" not in ci_text,
        "the string 3.12 still appears in ci.yml",
    )

    print()
    total = RESULTS["pass"] + RESULTS["fail"]
    print(f"{RESULTS['pass']} passed, {RESULTS['fail']} failed of {total}")
    if FAILURES:
        print(json.dumps([{"name": n, "detail": d} for n, d in FAILURES], indent=2))
    return 0 if RESULTS["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
