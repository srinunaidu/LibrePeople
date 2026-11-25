#!/usr/bin/env python3
"""Check that every third-party import the backend makes is declared.

The container installs `backend/requirements.txt` and nothing else. A module
that is in the CI dependency set, or in a developer's virtualenv, but not in
that file, imports in CI and fails in production — and the failure looks like
something else entirely: a migration that "cannot be located", or an
application that will not start.

That is not hypothetical. On 2026-10-22 the preset loader and the rule-pack
loader both imported `jsonschema`, which was not declared. The deploy failed
with `ModuleNotFoundError: No module named 'jsonschema'` and alembic reported
`Can't locate revision identified by '0011_tenant_preset_state'` — a revision
that was present, and could not be imported.

The check walks the import statements of every module the container ships and
compares the third-party ones with the requirements file. A module that a
package provides transitively — `starlette` through `fastapi`, `cryptography`
through `python-jose[cryptography]` — is resolved through the declared
packages, so it does not have to be declared on its own.

Usage:
    python ci/check_requirements.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "backend"
REQUIREMENTS = BACKEND / "requirements.txt"

#: The directories the container ships and that must import cleanly.
SHIPPED = ("app", "migrations", "scripts")

#: A module that a declared package provides, so it need not be declared.
#: An import name that differs from the package that provides it.
PACKAGE_OF = {
    "fpdf": "fpdf2",
    "jose": "python-jose",
    "dotenv": "python-dotenv",
}

TRANSITIVE = {
    "starlette": "fastapi",
    "cryptography": "python-jose[cryptography]",
    "pydantic_core": "pydantic",
    "anyio": "fastapi",
    "sniffio": "fastapi",
    "jinja2": "fastapi",
    "multipart": "python-multipart",
    "dotenv": "python-dotenv",
    "referencing": "jsonschema",
    "rpds": "jsonschema",
    "attrs": "jsonschema",
}


def declared() -> set[str]:
    names: set[str] = set()
    for line in REQUIREMENTS.read_text().split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        line = line.split("[", 1)[0]          # the extras are not the name
        for separator in ("==", ">=", "<=", "~=", ">", "<"):
            if separator in line:
                line = line.split(separator, 1)[0]
                break
        name = line.strip().lower().replace("_", "-")
        if name:
            names.add(name)
    return names


def local_modules() -> set[str]:
    names: set[str] = set()
    for package in (BACKEND / "app").rglob("*.py"):
        names.add(package.stem)
        parts = package.relative_to(BACKEND).with_suffix("").parts
        names.add(parts[-1])
        for i in range(len(parts) - 1):
            names.add(".".join(parts[i:]))
    return names


def imports_of(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found


def main() -> int:
    declared_names = declared()
    local = local_modules()
    stdlib = set(sys.stdlib_module_names)

    problems: dict[str, set[str]] = {}
    for package in SHIPPED:
        for path in sorted((BACKEND / package).rglob("*.py")):
            if path.name.startswith("test_"):
                # A test module is not imported by the application. It may
                # need pytest, which is not a runtime dependency.
                continue
            for name in imports_of(path):
                if name in stdlib or name in local or name == "app":
                    continue
                package = PACKAGE_OF.get(name, name).lower().replace("_", "-")
                if package in declared_names:
                    continue
                if name in TRANSITIVE:
                    continue
                problems.setdefault(name, set()).add(str(path.relative_to(REPO)))

    if not problems:
        print("requirements: every third-party import is declared")
        return 0

    print("requirements: these imports are not in backend/requirements.txt, so the")
    print("container cannot import them and the deploy will fail:")
    for name, paths in sorted(problems.items()):
        print(f"  {name}")
        for path in sorted(paths)[:3]:
            print(f"      {path}")
    print()
    print("Add it to backend/requirements.txt, pinned, and re-run this check.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
