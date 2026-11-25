#!/usr/bin/env python3
"""Merge the Karmathy OpenAPI fragments into a single contract document.

The contract tree under ``contracts/openapi/`` is the source of truth for
what the API promises.  Every domain owns one fragment; this script joins
the fragments with the shared components and writes one OpenAPI 3.1
document.

Usage
-----
    python scripts/merge_openapi.py            # write contracts/openapi/openapi.yaml
    python scripts/merge_openapi.py --check    # fail if the merged file is stale
    python scripts/merge_openapi.py --out /tmp/openapi.yaml

The script never touches the network and never edits a fragment.  It fails
loudly, with one line per problem, when:

  * two operations share an ``operationId``;
  * the same path (or the same path and method) is declared twice;
  * a path is declared by two fragments;
  * a ``$ref`` points at a component that does not exist;
  * an operation is missing an ``operationId``, a tag, a summary, a
    description or a response;
  * an ``x-lifecycle`` marker is not ``released`` or ``planned``.

Exit codes: 0 success, 1 the contract is invalid or (with ``--check``) the
merged file is out of date, 2 the contract tree could not be read.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:  # pragma: no cover - dependency guard
    sys.stderr.write("pyyaml is required: pip install pyyaml\n")
    raise SystemExit(2)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = REPO_ROOT / "contracts" / "openapi"
COMPONENTS_FILE = CONTRACT_DIR / "_components.yaml"
DEFAULT_OUT = CONTRACT_DIR / "openapi.yaml"

HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
LIFECYCLE_VALUES = ("released", "planned")
CAMEL_CASE = re.compile(r"^[a-z][a-zA-Z0-9]*$")

OPENAPI_VERSION = "3.1.0"
CONTRACT_VERSION = "1.0.0"
GENERATED_BY = "scripts/merge_openapi.py"

DESCRIPTION = """\
The contract of the Karmathy HCM API.

Karmathy is deployed once per customer. One deployment holds exactly one
customer's data in exactly one Oracle schema, and there is no cross tenant
querying anywhere in this API: a caller only ever sees the records of the
deployment it is talking to. Because of that, no endpoint takes a tenant
parameter.

Authentication is a bearer token issued by `POST /auth/login`. Every
operation except `authLogin` and `authRefresh` requires
`Authorization: Bearer <access_token>`.

Every error response uses the one envelope of `contracts/errors.md`:

    {"error": {"code": ..., "category": ..., "message": ...,
               "retryable": ..., "details": {...}, "request_id": ...}}

Clients branch on `error.code` and never on `error.message`.

This document is the authority for what the API *promises*. The running
application publishes its own generated document at
`GET /api/v1/openapi.json`, which is the authority for what the code
*does* today. `scripts/check_openapi_drift.py` compares the two.
"""


class ContractError(Exception):
    """Raised for a problem that must stop the merge."""


def fragment_files(contract_dir: Path) -> list[Path]:
    """Return the domain fragments, in a stable order.

    Files whose name starts with an underscore are private to a fragment
    and are not merged as domains. The generated ``openapi.yaml`` is the
    output of this script and is never an input.
    """
    files = [
        path
        for path in sorted(contract_dir.glob("*.yaml"))
        if not path.name.startswith("_") and path.name != DEFAULT_OUT.name
    ]
    if not files:
        raise ContractError(f"no domain fragments found in {contract_dir}")
    return files


def load_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise ContractError(f"{path}: file not found") from exc
    except yaml.YAMLError as exc:
        raise ContractError(f"{path}: invalid YAML: {exc}") from exc


def resolve_pointer(document: Any, pointer: str) -> tuple[bool, Any]:
    """Resolve a JSON pointer into a document.

    Returns ``(found, value)``. ``found`` is False when any step of the
    pointer is missing.
    """
    if pointer in ("", "/"):
        return True, document
    current = document
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                return False, None
            current = current[token]
        elif isinstance(current, list):
            try:
                index = int(token)
            except ValueError:
                return False, None
            if index < 0 or index >= len(current):
                return False, None
            current = current[index]
        else:
            return False, None
    return True, current


def iter_refs(node: Any, trail: str = "") -> Iterable[tuple[str, str]]:
    """Yield ``(ref, trail)`` for every ``$ref`` in a document tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            child_trail = f"{trail}/{key}"
            if key == "$ref" and isinstance(value, str):
                yield value, child_trail
            else:
                yield from iter_refs(value, child_trail)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from iter_refs(value, f"{trail}/{index}")


def build_document(contract_dir: Path) -> tuple[dict[str, Any], list[str]]:
    """Assemble the merged document.

    Returns the document and the list of problems found. The document is
    returned even when there are problems so that the caller can report
    every one of them at once.
    """
    problems: list[str] = []

    components_path = contract_dir / COMPONENTS_FILE.name
    if not components_path.exists():
        components_path = COMPONENTS_FILE
    components_doc = load_yaml(components_path)
    if not isinstance(components_doc, dict):
        raise ContractError(f"{components_path}: expected a mapping")
    components = components_doc.get("components", components_doc)
    if not isinstance(components, dict):
        raise ContractError(f"{components_path}: 'components' must be a mapping")

    paths: dict[str, Any] = {}
    path_owner: dict[str, str] = {}
    operation_owner: dict[str, str] = {}
    tags: list[dict[str, Any]] = []
    tag_names: set[str] = set()

    for fragment_path in fragment_files(contract_dir):
        name = fragment_path.name
        fragment = load_yaml(fragment_path)
        if not isinstance(fragment, dict):
            problems.append(f"{name}: the fragment must be a mapping")
            continue

        unknown = set(fragment) - {"paths", "tags"} - {k for k in fragment if k.startswith("x-")}
        if unknown:
            problems.append(
                f"{name}: unknown top level key(s) {sorted(unknown)}; "
                "a fragment may only carry 'paths', 'tags' and 'x-' extensions"
            )

        for tag in fragment.get("tags") or []:
            if not isinstance(tag, dict) or "name" not in tag:
                problems.append(f"{name}: every tag needs a name")
                continue
            if tag["name"] in tag_names:
                continue
            tag_names.add(tag["name"])
            tags.append(tag)

        fragment_paths = fragment.get("paths")
        if fragment_paths is None:
            problems.append(f"{name}: the fragment has no 'paths'")
            continue
        if not isinstance(fragment_paths, dict):
            problems.append(f"{name}: 'paths' must be a mapping")
            continue

        for path, path_item in fragment_paths.items():
            if not path.startswith("/"):
                problems.append(f"{name}: path {path!r} must start with '/'")
                continue
            if path in path_owner:
                problems.append(
                    f"duplicate path {path!r}: declared by {path_owner[path]} and by {name}"
                )
                continue
            path_owner[path] = name
            if not isinstance(path_item, dict):
                problems.append(f"{name}: path {path!r} must map to a path item")
                continue

            item_lifecycle = path_item.get("x-lifecycle")
            if item_lifecycle is not None and item_lifecycle not in LIFECYCLE_VALUES:
                problems.append(
                    f"{name}: path {path!r} has x-lifecycle {item_lifecycle!r}; "
                    f"expected one of {LIFECYCLE_VALUES}"
                )

            for method, operation in path_item.items():
                if method.startswith("x-"):
                    continue
                if method not in HTTP_METHODS:
                    problems.append(
                        f"{name}: path {path!r} has the unknown key {method!r}; "
                        "a path item only carries HTTP methods and x- extensions"
                    )
                    continue
                if not isinstance(operation, dict):
                    problems.append(f"{name}: {method.upper()} {path} must map to an operation")
                    continue

                operation_id = operation.get("operationId")
                if not operation_id:
                    problems.append(f"{name}: {method.upper()} {path} has no operationId")
                else:
                    if not isinstance(operation_id, str) or not CAMEL_CASE.match(operation_id):
                        problems.append(
                            f"{name}: operationId {operation_id!r} is not camelCase"
                        )
                    if operation_id in operation_owner:
                        problems.append(
                            f"duplicate operationId {operation_id!r}: "
                            f"{operation_owner[operation_id]} and "
                            f"{method.upper()} {path} in {name}"
                        )
                    else:
                        operation_owner[operation_id] = f"{method.upper()} {path} ({name})"

                op_tags = operation.get("tags")
                if not op_tags:
                    problems.append(f"{name}: {method.upper()} {path} has no tag")
                elif not isinstance(op_tags, list) or len(op_tags) != 1:
                    problems.append(
                        f"{name}: {method.upper()} {path} must carry exactly one tag"
                    )

                if not operation.get("summary"):
                    problems.append(f"{name}: {method.upper()} {path} has no summary")
                if not operation.get("description"):
                    problems.append(f"{name}: {method.upper()} {path} has no description")
                if not operation.get("responses"):
                    problems.append(f"{name}: {method.upper()} {path} has no responses")

                lifecycle = operation.get("x-lifecycle", item_lifecycle)
                if lifecycle is not None and lifecycle not in LIFECYCLE_VALUES:
                    problems.append(
                        f"{name}: {method.upper()} {path} has x-lifecycle {lifecycle!r}; "
                        f"expected one of {LIFECYCLE_VALUES}"
                    )

            paths[path] = path_item

    document: dict[str, Any] = {
        "openapi": OPENAPI_VERSION,
        "info": {
            "title": "Karmathy HCM API",
            "version": CONTRACT_VERSION,
            "description": DESCRIPTION,
            "x-generated-by": GENERATED_BY,
        },
        "servers": [
            {
                "url": "/api/v1",
                "description": (
                    "Deployment local API root. One deployment serves one customer "
                    "out of one Oracle schema."
                ),
            }
        ],
        "tags": sorted(tags, key=lambda tag: tag.get("name", "")),
        "security": [{"bearerAuth": []}],
        "paths": dict(sorted(paths.items())),
        "components": components,
    }

    # Every $ref has to resolve inside the merged document.
    for ref, trail in iter_refs(document):
        if not ref.startswith("#/"):
            problems.append(
                f"the reference {ref!r} at {trail} is not local to the merged document"
            )
            continue
        found, _value = resolve_pointer(document, ref[1:])
        if not found:
            problems.append(f"the reference {ref!r} at {trail} does not resolve")

    return document, problems


def dump_document(document: dict[str, Any]) -> str:
    """Render the document deterministically."""
    return yaml.safe_dump(
        document,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=100,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Merge the Karmathy OpenAPI fragments into one document.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; fail when the merged document is out of date",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"where to write the merged document (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--contract-dir",
        type=Path,
        default=CONTRACT_DIR,
        help="the directory that holds the fragments (default: contracts/openapi)",
    )
    args = parser.parse_args(argv)

    contract_dir: Path = args.contract_dir
    out_path: Path = args.out

    try:
        document, problems = build_document(contract_dir)
    except ContractError as exc:
        sys.stderr.write(f"merge_openapi: {exc}\n")
        return 2

    if problems:
        sys.stderr.write(f"merge_openapi: {len(problems)} problem(s) in the contract:\n")
        for problem in problems:
            sys.stderr.write(f"  - {problem}\n")
        return 1

    text = dump_document(document)

    if args.check:
        try:
            current = out_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            sys.stderr.write(
                f"merge_openapi: {out_path} does not exist; run scripts/merge_openapi.py\n"
            )
            return 1
        if current != text:
            sys.stderr.write(
                f"merge_openapi: {out_path} is out of date with the fragments.\n"
                "  The contract and the merged document disagree; "
                "run: python scripts/merge_openapi.py\n"
            )
            return 1
        print(f"merge_openapi: {out_path} is up to date")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    operations = sum(
        1
        for path_item in document["paths"].values()
        for method in path_item
        if method in HTTP_METHODS
    )
    print(
        f"merge_openapi: wrote {out_path} "
        f"({len(document['paths'])} paths, {operations} operations, "
        f"{len(document['tags'])} tags)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
