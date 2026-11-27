"""Verify a release manifest (update-system).

Checks, fail-closed (exit 1 on any failure):
1. The manifest validates against ``releases/manifest.schema.json``.
2. The checksum chain holds (``manifest_sha256`` == sha256 of canonical
   JSON minus the signature block).
3. The signature block is well-formed; ``dev-ephemeral`` passes with a
   loud CI warning (never silent), any other key id must be listed in
   ``UPDATE_SIGNING_KEY_IDS``. Full minisign cryptographic verification
   of a production signature is the owner-held offline ceremony; this
   script enforces the allow-list side of it.

Usage:
    python scripts/verify_release.py [path/to/manifest.json]
    (default: releases/manifest.json)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    import jsonschema  # type: ignore
except ImportError:  # pragma: no cover
    jsonschema = None


def canonical_bytes(manifest: dict) -> bytes:
    # The hash cannot cover itself: exclude both the signature block and
    # the manifest_sha256 field (same rule as make_release_manifest.py).
    body = {k: v for k, v in manifest.items() if k not in ("signature", "manifest_sha256")}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "releases" / "manifest.json"
    failures: list[str] = []
    warnings: list[str] = []

    try:
        manifest = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"FAIL: manifest not found: {target}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"FAIL: manifest is not valid JSON: {exc}", file=sys.stderr)
        return 1

    schema_path = REPO_ROOT / "releases" / "manifest.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"FAIL: schema not found: {schema_path}", file=sys.stderr)
        return 1

    if jsonschema is not None:
        try:
            jsonschema.Draft202012Validator(schema).validate(manifest)
            print("schema: OK")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"schema validation failed: {exc}")
    else:
        missing = [f for f in schema.get("required", []) if f not in manifest]
        if missing:
            failures.append(f"schema check failed, missing fields: {missing}")
        else:
            warnings.append("jsonschema not installed: ran required-fields check only")
            print("schema: OK (required-fields only, jsonschema not installed)")

    expected = hashlib.sha256(canonical_bytes(manifest)).hexdigest()
    if manifest.get("manifest_sha256") == expected:
        print("checksum chain: OK")
    else:
        failures.append("manifest_sha256 mismatch: manifest was edited after signing")

    sig = manifest.get("signature") or {}
    key_id = str(sig.get("key_id") or "")
    if key_id == "dev-ephemeral":
        warnings.append(
            "dev-ephemeral signature: NOT A PRODUCTION RELEASE "
            "(keyless dev signature, checksum chain only)"
        )
        print("signature: dev-ephemeral (DEV ONLY — CI warns)")
    else:
        allowed = {
            part.strip()
            for part in os.environ.get("UPDATE_SIGNING_KEY_IDS", "").split(",")
            if part.strip()
        }
        if sig.get("alg") == "minisign" and key_id and key_id in allowed:
            print(f"signature: minisign key_id {key_id} allow-listed — OK")
        else:
            failures.append(
                f"signature key_id {key_id!r} is not dev-ephemeral and is not in "
                "UPDATE_SIGNING_KEY_IDS (owner-held pubkey IDs)"
            )

    for warning in warnings:
        print(f"WARNING: {warning}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(f"VERIFY OK: {target} version={manifest.get('version')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
