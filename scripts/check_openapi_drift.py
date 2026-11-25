#!/usr/bin/env python3
"""Compare the Karmathy OpenAPI contract with the running application.

Two sources are compared:

  * the **contract** - ``contracts/openapi/openapi.yaml``, the merged
    document built from the fragments in ``contracts/openapi/``. It is the
    authority for what the API *promises*.
  * the **application** - the document the running code generates. It is
    the authority for what the code *does* today.

The asymmetry is the whole point of this tool:

  * **The contract promises something the application does not serve:
    a hard failure.** A published contract that the server does not
    honour is the dangerous direction, so the check fails and CI goes red.
    The one exception is an operation that the contract itself marks
    ``x-lifecycle: planned``: that is a promise the contract has not made
    yet, so it is reported as "contract ahead of code" and does not fail.
  * **The application serves something the contract does not declare: a
    warning.** The contract is never edited automatically. The undeclared
    endpoints are listed for the coordinator to triage.
  * **A different ``operationId`` for the same route: a warning.** The
    generated id of the application is authoritative until the code
    changes.

Usage
-----
    python scripts/check_openapi_drift.py --app https://karmathy-backend.onrender.com
    python scripts/check_openapi_drift.py --spec https://example.test/openapi.json
    python scripts/check_openapi_drift.py --spec ./some-spec.json
    python scripts/check_openapi_drift.py --app https://host --no-report

Exit codes: 0 no hard failure, 1 the contract promises something the
application does not serve, 2 the check could not be run.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - dependency guard
    sys.stderr.write("pyyaml is required: pip install pyyaml\n")
    raise SystemExit(2)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = REPO_ROOT / "contracts" / "openapi" / "openapi.yaml"
DEFAULT_REPORT = REPO_ROOT / "contracts" / "openapi" / "_undeclared.md"

HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
API_PREFIXES = ("/api/v1", "/api")
LIFECYCLE_RELEASED = "released"
LIFECYCLE_PLANNED = "planned"


# --------------------------------------------------------------- helpers --


def normalise_path(path: str) -> str:
    """Strip the API prefix and the trailing slash from a path."""
    value = (path or "").strip()
    for prefix in API_PREFIXES:
        if value == prefix:
            return "/"
        if value.startswith(prefix + "/"):
            value = value[len(prefix):]
            break
    if len(value) > 1 and value.endswith("/"):
        value = value[:-1]
    return value or "/"


def path_shape(path: str) -> str:
    """Replace the path parameters by a placeholder.

    ``/payroll/runs/{run_id}`` and ``/payroll/runs/{id}`` are the same
    route; the spelling of the parameter is documentation, not identity.
    """
    return re.sub(r"\{[^}]*\}", "{}", path)


def is_api_path(path: str) -> bool:
    """True when a path belongs to the API surface (not to /health and friends)."""
    value = (path or "").strip()
    return any(value == prefix or value.startswith(prefix + "/") for prefix in API_PREFIXES)


def load_spec_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        document = yaml.safe_load(text)
    else:
        document = json.loads(text)
    if not isinstance(document, dict) or "paths" not in document:
        raise ValueError(f"{path}: not an OpenAPI document (no 'paths')")
    return document


def fetch_spec(url: str, timeout: float) -> dict[str, Any]:
    """Fetch an OpenAPI document over HTTP."""
    try:
        import httpx
    except ImportError:  # pragma: no cover - dependency guard
        raise RuntimeError("httpx is required to read a spec over HTTP") from None

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return _parse_spec(response.text, url)


def _parse_spec(text: str, url: str) -> dict[str, Any]:
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        try:
            document = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ValueError(f"{url}: the response is not an OpenAPI document: {exc}") from None
    if not isinstance(document, dict) or "paths" not in document:
        raise ValueError(f"{url}: the response is not an OpenAPI document (no 'paths')")
    return document


def app_openapi_url(base: str) -> str:
    """Turn an application base URL into the URL of its OpenAPI document."""
    value = base.rstrip("/")
    if value.endswith(".json"):
        return value
    if value.endswith("/api/v1"):
        return value + "/openapi.json"
    return value + "/api/v1/openapi.json"


# ------------------------------------------------------------- comparison --


def collect_operations(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """Index the operations of a document by (path shape, method)."""
    operations: dict[tuple[str, str], dict[str, Any]] = {}
    for raw_path, path_item in (document.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            key = (path_shape(normalise_path(raw_path)), method)
            operations[key] = {
                "raw_path": normalise_path(raw_path),
                "source_path": raw_path,
                "path_item": path_item,
                "operation": operation,
            }
    return operations


def lifecycle_of(path_item: dict[str, Any], operation: dict[str, Any]) -> str:
    """The lifecycle marker of an operation: operation first, then the path item."""
    value = operation.get("x-lifecycle")
    if value is None:
        value = path_item.get("x-lifecycle")
    return value or LIFECYCLE_RELEASED


def compare(contract: dict[str, Any], application: dict[str, Any]) -> dict[str, Any]:
    """Compare the two documents and return the findings."""
    contract_ops = collect_operations(contract)
    app_ops = collect_operations(application)

    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    ahead: list[dict[str, Any]] = []
    matched: list[dict[str, Any]] = []

    for (shape, method), entry in sorted(contract_ops.items()):
        operation = entry["operation"]
        contract_path = entry["raw_path"]
        operation_id = operation.get("operationId", "<no operationId>")
        app_entry = app_ops.get((shape, method))
        if app_entry is None:
            finding = {
                "path": contract_path,
                "method": method,
                "operation_id": operation_id,
            }
            if lifecycle_of(entry["path_item"], operation) == LIFECYCLE_PLANNED:
                ahead.append(finding)
            else:
                failures.append(finding)
            continue

        matched.append(
            {
                "path": contract_path,
                "method": method,
                "operation_id": operation_id,
                "app_path": app_entry["raw_path"],
            }
        )
        app_operation_id = app_entry["operation"].get("operationId")
        if app_operation_id and app_operation_id != operation_id:
            warnings.append(
                {
                    "kind": "operationId",
                    "path": contract_path,
                    "method": method,
                    "contract": operation_id,
                    "application": app_operation_id,
                }
            )
        if app_entry["raw_path"] != contract_path:
            warnings.append(
                {
                    "kind": "path-parameter-name",
                    "path": contract_path,
                    "method": method,
                    "contract": contract_path,
                    "application": app_entry["raw_path"],
                }
            )

    contract_keys = set(contract_ops)
    undeclared: list[dict[str, Any]] = []
    out_of_scope: list[str] = []
    for (shape, method), entry in sorted(app_ops.items()):
        if not is_api_path(entry["source_path"]):
            # /health and the like are not part of the API surface.
            out_of_scope.append(entry["raw_path"])
            continue
        if (shape, method) in contract_keys:
            continue
        undeclared.append(
            {
                "path": entry["raw_path"],
                "method": method,
                "operation_id": entry["operation"].get("operationId", "<no operationId>"),
            }
        )

    return {
        "failures": failures,
        "warnings": warnings,
        "ahead": ahead,
        "matched": matched,
        "undeclared": undeclared,
        "out_of_scope": sorted(out_of_scope),
        "contract_count": len(contract_ops),
        "application_count": len(app_ops),
    }


# ---------------------------------------------------------------- report --


def write_report(path: Path, findings: dict[str, Any], contract_name: str, app_name: str) -> None:
    """Write the triage report for the undeclared endpoints."""
    lines: list[str] = []
    lines.append("# Undeclared endpoints")
    lines.append("")
    lines.append(
        "Generated by `scripts/check_openapi_drift.py`. The running application "
        "serves these endpoints and the contract does not declare them. The "
        "contract is **not** edited automatically: the coordinator triages this "
        "list and either adds the endpoint to the owning lane's fragment or "
        "records that the endpoint is private to the application."
    )
    lines.append("")
    lines.append(f"* contract: `{contract_name}`")
    lines.append(f"* application: `{app_name}`")
    lines.append("")
    lines.append(f"## Undeclared endpoints ({len(findings['undeclared'])})")
    lines.append("")
    if not findings["undeclared"]:
        lines.append("None. Every endpoint of the application is declared in the contract.")
    else:
        lines.append("| Method | Path | Application operationId |")
        lines.append("|---|---|---|")
        for item in findings["undeclared"]:
            lines.append(f"| {item['method'].upper()} | `{item['path']}` | `{item['operation_id']}` |")
    lines.append("")
    lines.append("## Other findings")
    lines.append("")
    lines.append(f"* operationId mismatches (warning): {len(findings['warnings'])}")
    lines.append(f"* contract operations the application does not serve (failure): {len(findings['failures'])}")
    lines.append(f"* contract operations that are ahead of the code (planned): {len(findings['ahead'])}")
    lines.append("")
    if findings["out_of_scope"]:
        lines.append(
            "Paths outside the API surface (not compared, listed for completeness): "
            + ", ".join(f"`{p}`" for p in findings["out_of_scope"])
        )
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def print_summary(findings: dict[str, Any], contract_name: str, app_name: str) -> None:
    """Print the human readable result."""
    print("Karmathy OpenAPI drift check")
    print(f"  contract   : {contract_name}")
    print(f"  application: {app_name}")
    print(
        f"  operations : {findings['contract_count']} in the contract, "
        f"{findings['application_count']} in the application"
    )
    print("")

    if findings["failures"]:
        print(f"HARD FAILURES ({len(findings['failures'])}): the contract promises these "
              "endpoints and the application does not serve them")
        for item in findings["failures"]:
            print(f"  - {item['method'].upper()} {item['path']}  [{item['operation_id']}]")
        print("")

    if findings["ahead"]:
        print(f"CONTRACT AHEAD OF CODE ({len(findings['ahead'])}): declared as "
              "x-lifecycle: planned, not promised yet, not a failure")
        for item in findings["ahead"]:
            print(f"  - {item['method'].upper()} {item['path']}  [{item['operation_id']}]")
        print("")

    if findings["warnings"]:
        print(f"WARNINGS ({len(findings['warnings'])}): the application is authoritative "
              "until the code changes")
        for item in findings["warnings"]:
            if item["kind"] == "operationId":
                print(
                    f"  - {item['method'].upper()} {item['path']}: operationId "
                    f"{item['contract']} (contract) vs {item['application']} (application)"
                )
            else:
                print(
                    f"  - {item['method'].upper()} {item['path']}: the contract spells the "
                    f"path {item['contract']}, the application {item['application']}"
                )
        print("")

    if findings["undeclared"]:
        print(f"UNDECLARED ENDPOINTS ({len(findings['undeclared'])}): the application "
              "serves these, the contract does not declare them")
        for item in findings["undeclared"]:
            print(f"  - {item['method'].upper()} {item['path']}  [{item['operation_id']}]")
        print("")

    print(f"matched    : {len(findings['matched'])}")
    if findings["out_of_scope"]:
        print(
            "out of scope: "
            + ", ".join(findings["out_of_scope"])
            + " (not part of the API surface, not compared)"
        )
    print("")


# ------------------------------------------------------------------ main --


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare the Karmathy OpenAPI contract with the running application.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--app",
        metavar="URL",
        help="base URL of the running application; the OpenAPI document is fetched from {app}/api/v1/openapi.json",
    )
    source.add_argument(
        "--spec",
        metavar="URL_OR_PATH",
        help="an OpenAPI document to compare against: an URL (httpx) or a local file",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=DEFAULT_CONTRACT,
        help=f"the merged contract to compare (default: {DEFAULT_CONTRACT})",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"where to write the undeclared endpoints report (default: {DEFAULT_REPORT})",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="do not write the report file",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="timeout in seconds for the HTTP request (default: 60)",
    )
    args = parser.parse_args(argv)

    try:
        contract = load_spec_document(args.contract)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        sys.stderr.write(f"check_openapi_drift: cannot read the contract: {exc}\n")
        sys.stderr.write("  run: python scripts/merge_openapi.py\n")
        return 2

    app_name = ""
    try:
        if args.app:
            url = app_openapi_url(args.app)
            app_name = url
            application = fetch_spec(url, args.timeout)
        else:
            spec = args.spec
            if re.match(r"^https?://", spec):
                app_name = spec
                try:
                    application = fetch_spec(spec, args.timeout)
                except Exception as exc:  # noqa: BLE001 - fall back to the API path
                    fallback = app_openapi_url(spec)
                    if fallback == spec:
                        raise
                    app_name = fallback
                    application = fetch_spec(fallback, args.timeout)
            else:
                spec_path = Path(spec)
                application = load_spec_document(spec_path)
                app_name = str(spec_path)
    except Exception as exc:  # noqa: BLE001 - the check could not be run
        sys.stderr.write(f"check_openapi_drift: cannot read the application spec: {exc}\n")
        return 2

    findings = compare(contract, application)
    print_summary(findings, str(args.contract), app_name)

    if not args.no_report:
        try:
            write_report(args.report, findings, str(args.contract), app_name)
            print(f"report     : {args.report}")
        except OSError as exc:
            sys.stderr.write(f"check_openapi_drift: cannot write the report: {exc}\n")
            return 2

    if findings["failures"]:
        print(
            f"RESULT: FAIL - {len(findings['failures'])} promised endpoint(s) are not "
            "served by the application."
        )
        return 1

    print("RESULT: OK - the application serves everything the contract promises.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
